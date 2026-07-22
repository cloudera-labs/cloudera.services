> Part of the cloudera.services agent guide — see [AGENTS.md](../AGENTS.md).

# Authoring Modules

## Naming Conventions

- **Modules**: `{service}_{entity}.py` (e.g., `ssb_project.py`)
- **Info modules**: `{service}_{entity}_info.py` (read-only queries)
- **Module utils**: `{service}.py` or `cdp_{service}.py`
- **Test files**: `test_{module_name}_{type}.py` (or `test_{module_name}_{type}_int.py` for integration)

## Module Structure Template

```python
DOCUMENTATION = r"""
module: service_entity
short_description: Brief description (< 50 chars)
description:
  - Detailed description
  - The module supports check_mode
extends_documentation_fragment: cloudera.services.services_client
options:
  parameter_name:
    description: What it does
    type: str
    required: true
attributes:
  check_mode:
    support: full
  diff_mode: # Only if applicable
    support: full
  platform:
    platforms: all
"""

EXAMPLES = r"""
- name: Example task
  cloudera.services.service_entity:
    endpoint: "{{ service_endpoint }}"
    username: "{{ service_username }}"
    password: "{{ service_password }}"
    name: resource_name
    state: present
"""

RETURN = r"""
resource:
    description: Resource details
    returned: on success
    type: dict
"""

class ServiceEntityModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(**Model.argument_spec(), state=...),
            supports_check_mode=True,
        )

    def process(self):
        # Implement logic
        # Set self.changed and self.diff
```

## Development Workflow

1. Create/modify plugin in `plugins/<plugin_type>/<plugin_family>/<plugin_name>/`
2. Update DOCUMENTATION/EXAMPLES/RETURN strings
3. Validate: `ansible-doc -t <plugin_type> cloudera.services.<plugin_name>`
4. Write unit tests in `tests/unit/plugins/<plugin_type>/<plugin_family>/<plugin_name>/`
5. Write integration tests in `tests/unit/plugins/<plugin_type>/<plugin_family>/<plugin_name>/` with `_int.py` suffix and use `env_context` for env var checks
6. Run tests: `pytest tests/unit/ <plugin name filter>`
7. Run linter: `hatch run lint`
8. Build collection: `ansible-galaxy collection build`
9. Regenerate docs: `hatch run docs:build`

See [documentation.md](documentation.md) for doc-string conventions and [testing.md](testing.md) for test patterns.
