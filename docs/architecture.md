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

Entity instances (the objects typedefs describe, such as a `hive_table`) use a separate client, `AtlasEntityClient` in `plugins/module_utils/atlas_entity.py`, with one module per aspect: `atlas_entity_info` looks an entity up, `atlas_entity_label`, `atlas_entity_business_metadata` and `atlas_entity_classification` manage one aspect of it, and `atlas_entity` creates, updates and deletes the entity itself. It reuses the case-conversion helpers from `atlas.py`.

- **Identity:** an entity is addressed by `guid`, or by `type_name` plus unique attributes (usually `qualified_name`, shorthand for the `qualifiedName` attribute), sent as `attr:<name>=<value>` query parameters. Quote any value used in a URL path with `urllib.parse.quote(value, safe="")`
- **Verbatim maps:** `attributes`, `relationship_attributes`, `custom_attributes` and `business_attributes` hold Atlas attribute names (`qualifiedName`), which must never be snake-cased. Pass them as `verbatim_values` to `snake_preserving_options()` / `camel_preserving_options()` (`ENTITY_VERBATIM_VALUES`): the map's own key is converted, its contents are not. This differs from `verbatim_keys`, which also leaves the key itself alone
- **Lookups:** a 404 is squelched to `None` on reads only. An unknown *type* is an HTTP 400, so a mistyped type name fails instead of reading as a missing entity. A lookup by unique attributes never returns a deleted entity, but a lookup by guid does, with `status: DELETED`
- **Response shape:** validate it before `from_dict`; a malformed body must raise `ServicesError`, not a `TypeError` for a missing required field
- **Labels:** `set_entity_labels()` POSTs the whole list, because a DELETE request body does not reach Atlas through Knox. `atlas_entity_label` therefore reads the current labels, works out the target list (add, `exclusive`, or remove) and writes only when the sets differ. Atlas omits `labels` for an unlabelled entity, so treat a non-list value as empty. Check labels with `validate_labels()` before any request; Atlas allows only letters, digits, `_` and `-`
- **Business metadata:** `set_entity_business_metadata()` POSTs to `/businessmetadata/{name}` with `isOverwrite=false` (merge within that business metadata) and `remove_entity_business_metadata()` DELETEs the whole business metadata; never send `isOverwrite=true`, which wipes the entity's other business metadata. `businessAttributes` (`{bmName: {attr: value}}`) is on the full entity GET only, not on `/header`. `atlas_entity_business_metadata` reads the business metadata typedef and passes the requested attributes through `normalize_business_attributes()`, which fails on unknown attribute names and nulls and converts values to the declared type, then sends only the attributes that differ. Both steps are needed because Atlas silently ignores unknown attributes and stores `"5"` for an `int` as `5`
- **Classifications:** an entity's `classifications` (full entity GET, not only `/header`) lists the ones attached directly *and* the ones propagated from other entities; a propagated one carries the origin's `entityGuid`. `atlas_entity_classification` manages only the direct ones (`entityGuid` unset or equal to the entity's guid). `add_entity_classifications()` (POST) fails if one is already attached and `update_entity_classifications()` (PUT) fails if none is, so the module reads first and picks one; `remove_entity_classification()` DELETEs by name with no body. Atlas merges the attributes of a PUT but not the other fields, so the module re-sends the current `propagate`, `remove_propagations_on_entity_delete` and `validity_periods`, plus the merged attributes. Attribute names are checked with `classification_attribute_defs()`, which follows `super_types` because a classification inherits their attributes, then `normalize_attributes()` (shared with business metadata). After a write the module re-reads the entity so it can return the classification as Atlas stored it, with its defaults
- **Entity itself:** `atlas_entity` owns only `attributes` and `custom_attributes`; the other aspects each have their own module. It creates with `create_entity()` (POST), and updates an existing entity with `update_entity_by_unique_attributes()`, a partial PUT, because a POST of an existing entity fails unless it carries every mandatory attribute (HTTP 404, `ATLAS-404-00-007`). Only the differing attributes are sent, and names and values are checked against the type's attributes, including those of its super types (`entity_attribute_defs()`, sharing its traversal with `classification_attribute_defs()`), then converted by `normalize_attributes()`. The unique attributes are merged into the attributes of a new entity and are never part of an update. Custom attributes are sent as the existing map plus the new keys, since Atlas may replace the whole map. `delete_entity_by_guid()` returns the guids Atlas reports as deleted, because the delete can cascade to owned entities and the response is a silent 200 for an unknown guid. The module refuses a type whose typedef has a `service_type` (a hook-owned type such as `hive_table`) unless `allow_service_types` is set, and verifies the status after every write (`ACTIVE` after create and update, `DELETED` after delete, where a missing entity also counts as deleted)
- **Aspect modules and missing entities:** a module that changes an aspect of an existing entity fails under `present` when the entity is missing or not `ACTIVE`, and does nothing under `absent`

## Apache Atlas Glossary

Glossaries, categories and terms use their own client, `AtlasGlossaryClient` in `plugins/module_utils/atlas_glossary.py` (REST base `/api/atlas/v2/glossary`), with one module per resource. The client grows with the modules; so far it covers glossaries (`atlas_glossary_info`, `atlas_glossary`).

- **Field names:** the models use `name`, not the `displayName` of older Atlas documentation. Only `qualifiedName` is unique, so a name can match several glossaries; the info module returns every match and a module that manages a glossary must fail on ambiguity
- **Responses omit empty fields:** null fields and empty `terms`/`categories` sets are absent from a GET, not `[]`. `terms` and `categories` on a glossary are headers (`AtlasRelatedTermHeader`, `AtlasRelatedCategoryHeader`), not full objects
- **Verbatim maps:** `additionalAttributes` is user data; pass `GLOSSARY_VERBATIM_VALUES` as `verbatim_values` to the case-conversion helpers, with `verbatim_keys=()` and `verbatim_map_keys=()` as the entity client does
- **Lookups:** a glossary is looked up by guid (a 404 is squelched to `None`) or found by listing, `GET /v2/glossary?limit=-1`, and filtering client-side. Deletes are hard (no `DELETED` status and nothing to purge), so a deleted glossary is simply unknown and its name can be used again
- **Delete:** `DELETE` removes the glossary together with every term and category in it, and Atlas refuses (HTTP 400, `ATLAS-400-00-084`) while any term is assigned to an entity. Unlike an entity delete, an unknown guid is a 404, which the client squelches
- **Updates are partial:** `partial_update_glossary()` PUTs only the changed fields to `/{guid}/partial` (`name`, `short_description`, `long_description`, `language`, `usage`; an empty string clears one). The full `PUT /{guid}` is deliberately not offered, because it deletes every field the body omits. The qualified name is immutable, so a rename changes `name` only and a glossary that is renamed is identified by `guid` or `qualified_name`
- **`atlas_glossary` identity and delete guard:** identity is `guid`, `qualified_name`, or `name` (several glossaries can share a name, so ambiguity fails). `state=absent` refuses a glossary that holds terms or categories unless `cascade` is set, and always refuses while a term is assigned to an entity: it reads the terms with `list_terms()` (`GET /{guid}/terms` carries `assignedEntities`; a `DELETED` relationship does not count) and fails before the DELETE. Check mode predicts the same refusals. Failures are raised as `ServicesError`, which `ServicesModule.execute()` turns into `fail_json`

## State Management

- Standard states: `present`, `absent`
- Some modules: `started`, `stopped`, `synced`, `published`
- Implement idempotency through existence checks
- Use `diff_dict()` to detect changes
- Validate immutable fields and fail if they change after creation
- Restrict to declarative state management rather than imperative actions
