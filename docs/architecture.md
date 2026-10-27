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
- A dataclass with an `argument_spec()` classmethod (optional fields `Union[T, None, NULLABLE]`), the `get_<category>_def_by_name`, `create_<category>_def` and `update_<category>_def` client methods, and an `extract_<category>_def_params()` helper
- Reuse `delete_typedef_by_name()`; deleting a missing typedef is a no-op

Conventions:
- **Bundles:** Atlas writes go to `/api/atlas/v2/types/typedefs` as a bundle, `{"<category>Defs": [def]}`. The client sends one def and keeps the module single-resource. Pick the written def out of the response by name with `_written_def()` (every category uses it), which raises `ServicesError` when the bundle lacks it
- **Not found:** a 404 on read is squelched to `None`
- **Verbatim maps:** free-form maps (`options`, `params`) and maps keyed by user-chosen names (`business_attribute_defs`) must not be camelCased or snake_cased. Add new ones to `VERBATIM_KEYS` or `VERBATIM_MAP_KEYS`
- **Idempotence:** Atlas fills in defaults on the server (attribute flags, enum ordinals). `build_from_params(..., existing=existing)` replaces nested lists wholesale, so call `align_attribute_defs()`, `align_enum_elements()` or, for a relationship's `end_def1`/`end_def2`, `align_relationship_end_def()` before `diff_dict()`. Otherwise unset fields register as a change on every run
- **Forced deletes:** `delete_typedef_by_name(name, force=True)` sends `?force=true`. Atlas requires it to delete business metadata that has non-indexable attributes, so `atlas_business_metadata_def` exposes it as an opt-in `force` option

## State Management

- Standard states: `present`, `absent`
- Some modules: `started`, `stopped`, `synced`, `published`
- Implement idempotency through existence checks
- Use `diff_dict()` to detect changes
- Validate immutable fields and fail if they change after creation
- Restrict to declarative state management rather than imperative actions
