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

## State Management

- Standard states: `present`, `absent`
- Some modules: `started`, `stopped`, `synced`, `published`
- Implement idempotency through existence checks
- Use `diff_dict()` to detect changes
- Validate immutable fields and fail if they change after creation
- Restrict to declarative state management rather than imperative actions
