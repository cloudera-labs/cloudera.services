> Part of the cloudera.services agent guide — see [AGENTS.md](../AGENTS.md).

# Architecture Patterns

## Module Base Classes

The collection uses two architectures:

**Modern (preferred for new modules):**
- Inherit from `ServicesModule` in `plugins/module_utils/common.py`
- Uses `AnsibleServicesClient` for HTTP operations
- Implements `AutoExecuteMeta` metaclass (auto-calls `execute()` after `__init__`)
- Abstract `process()` method contains business logic
- Built-in pagination via `@paginated()` decorator — parametrizable for non-default conventions: `@paginated(next_key="next_page_token", token_param="page_token", size_param="page_size")` handles CML's snake_case scheme; bare `@paginated()` keeps the camelCase default (`nextPageToken`/`pageToken`/`pageSize`)
- Custom auth/transport via the `build_api_client()` factory hook — override to return an authenticated `AnsibleServicesClient` subclass (see [authentication.md](authentication.md))

**Legacy:**
- Inherit from `CdpRestModule` (and variants: `CdpSsbModule`, `CdpEfmModule`, `MLModule`, `RangerModule`)
- Direct `requests.Session` usage
- Migrated to the modern architecture whenever possible, but some older modules still use this pattern

## Data Model Pattern

Use dataclasses with `NULLABLE` sentinel:
```python
from plugins.module_utils.common import NULLABLE, from_dict, to_dict, diff_dict

@dataclass
class MyResource:
    id: Union[int, None, NULLABLE] = NULLABLE
    name: Union[str, None, NULLABLE] = NULLABLE
```

- `NULLABLE` distinguishes unset from `None`
- `from_dict()` / `to_dict()` for serialization
- `diff_dict()` for computing changes between instances

## Client Separation

Separate concerns:
- **Module class**: Ansible orchestration, parameter handling, state management
- **Client class**: REST API operations, HTTP calls
- **Model dataclass**: Data structure definition

Example:
```python
class SsbProjectModule(ServicesModule):
    def process(self):
        client = SsbProjectClient(self.api_client)
        # Use client for operations

class SsbProjectClient:
    def create_project(self, project: SsbProject) -> SsbProject:
        # API calls here
```

## Apache Atlas Typedefs

All Atlas type definitions share one client, `AtlasTypeDefClient` in `plugins/module_utils/atlas.py`, with one module per category (`atlas_enum_def`, `atlas_classification_def`, `atlas_entity_def`, `atlas_struct_def`, `atlas_relationship_def`, `atlas_business_metadata_def`) and a read-only `atlas_typedef_info`. To add a category:
- A dataclass with an `argument_spec()` classmethod (optional fields `Union[T, None, NULLABLE]`)
- A `_TypeDefKind` constant holding the dataclass, URL segment and bundle key, such as `_STRUCT = _TypeDefKind(AtlasStructDef, "structdef", "structDefs")`. It converts with the generic camelCase/snake_case helpers. Pass `to_payload`/`from_response` only when a category needs more; enum does, to number element ordinals and to leave a `null` `options` unset
- The public `get_<category>_def_by_name`, `create_<category>_def` and `update_<category>_def` client methods, each a one-line delegate to `_get_def(kind, name)` or `_write_def(self.api_client.post | .put, kind, typedef)`. Keep the public names, because the module tests patch them
- An `extract_<category>_def_params()` wrapper over `_extract_params(module, Cls.argument_spec())`. Add a cleaner to `_LIST_PARAM_CLEANERS` or `_DICT_PARAM_CLEANERS` only for a new nested suboption key; they drop the `None`s Ansible fills in for unset suboptions, and never touch the inside of `options` or `params`
- Reuse `delete_typedef_by_name()`; deleting a missing typedef is a no-op

Conventions:
- **Bundles:** Atlas writes go to `/api/atlas/v2/types/typedefs` as a bundle, `{"<category>Defs": [def]}`. The client sends one def and keeps the module single-resource. Pick the written def out of the response by name with `_written_def()` (every category uses it), which raises `ServicesError` when the bundle lacks it
- **Not found:** a 404 on read is squelched to `None`
- **Verbatim maps:** free-form maps (`options`, `params`) and maps keyed by user-chosen names (`business_attribute_defs`) must not be camelCased or snake_cased. Add new ones to `VERBATIM_KEYS` or `VERBATIM_MAP_KEYS`
- **Idempotence:** Atlas fills in defaults on the server (attribute flags, enum ordinals). `build_from_params(..., existing=existing)` replaces nested lists wholesale, so call `align_attribute_defs()`, `align_enum_elements()` or, for a relationship's `end_def1`/`end_def2`, `align_relationship_end_def()` before `diff_dict()`. Otherwise unset fields register as a change on every run. These share `_fill_unset()` (take each unset field from the existing item; an explicit `None` counts as set) and `_align_by_key()`; a new keyed list is one more `_align_by_key(incoming, existing, "<key>")` call
- **Forced deletes:** `delete_typedef_by_name(name, force=True)` sends `?force=true`. Atlas requires it to delete business metadata that has non-indexable attributes, so `atlas_business_metadata_def` exposes it as an opt-in `force` option

## Apache Atlas Entities

Entity instances (the objects typedefs describe, such as a `hive_table`) use a separate client, `AtlasEntityClient` in `plugins/module_utils/atlas_entity.py`, with one module per aspect: `atlas_entity_info` looks an entity up, and later modules manage its labels, business metadata, classifications and the entity itself. It reuses the case-conversion helpers from `atlas.py`.

- **Identity:** an entity is addressed by `guid`, or by `type_name` plus unique attributes (usually `qualified_name`, shorthand for the `qualifiedName` attribute), sent as `attr:<name>=<value>` query parameters. Quote any value used in a URL path with `urllib.parse.quote(value, safe="")`
- **Verbatim maps:** `attributes`, `relationship_attributes`, `custom_attributes` and `business_attributes` hold Atlas attribute names (`qualifiedName`), which must never be snake-cased. Pass them as `verbatim_values` to `snake_preserving_options()` / `camel_preserving_options()` (`ENTITY_VERBATIM_VALUES`): the map's own key is converted, its contents are not. This differs from `verbatim_keys`, which also leaves the key itself alone
- **Lookups:** a 404 is squelched to `None` on reads only. An unknown *type* is an HTTP 400, so a mistyped type name fails instead of reading as a missing entity. A lookup by unique attributes never returns a deleted entity, but a lookup by guid does, with `status: DELETED`
- **Response shape:** validate it before `from_dict`; a malformed body must raise `ServicesError`, not a `TypeError` for a missing required field

## State Management

- Standard states: `present`, `absent`
- Some modules: `started`, `stopped`, `synced`, `published`
- Implement idempotency through existence checks
- Use `diff_dict()` to detect changes
- Validate immutable fields and fail if they change after creation
- Restrict to declarative state management rather than imperative actions
