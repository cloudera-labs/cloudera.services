> Part of the cloudera.services agent guide — see [AGENTS.md](../AGENTS.md).

# Testing Patterns

For the list of environment variables each service's integration tests require, see the repo-root
[TESTING.md](../TESTING.md).

**Use pytest, not `ansible-test`.** All unit and integration tests run under pytest directly.
Do not add `ansible-test sanity`/`units` steps to workflows or CI guidance here. Run a single file
or a filtered subset with the collections root on `PYTHONPATH`:

```bash
PYTHONPATH=/path/to/collections python3 -m pytest tests/unit/plugins/modules/ml/ -p no:cacheprovider -q
```

**Basename collisions.** Tests run in pytest's prepend import mode and the tree has no `__init__.py`,
so two test files with the **same basename** in different directories collide on import. Keep test
basenames unique across the tree (the `_module`/`_module_int` and per-resource naming below does this).

## Unit Tests

Use pytest with fixtures from `tests/unit/conftest.py`:

```python
def test_create_resource(module_args, mocker):
    # Setup
    mock_method = mocker.patch("module_utils.client.Client.create", return_value=...)
    module_args({"endpoint": "https://example.com", "name": "test"})

    # Execute
    with pytest.raises(AnsibleExitJson) as e:
        module.main()

    # Assert
    result = e.value.args[0]
    assert result["changed"] is True
    mock_method.assert_called_once()
```

**Integration tests:**
- Suffix: `_int.py`
- Declare `REQUIRED_ENV_VARS = [...]` at module top; combined with the `env_context` fixture, tests skip cleanly when creds are absent (e.g. `CML_ENDPOINT`/`CML_API_KEY`)
- Test against live APIs with proper environment variables set using the `env_context` fixture
- **Clean up after themselves via fixture factories** (defined in `tests/unit/conftest.py`). Live-CRUD tests must not leave orphaned resources. Follow the SSB pattern:
  - `purge_<resource>` — a factory the test calls with the created object; deletes it on teardown (use for create tests: `purge_ml_project(from_dict(MlProject, result["project"]))`)
  - `existing_<resource>` — module-scoped, provisions a shared resource and removes it at teardown (use for idempotent / by-id / check-mode-delete reads)
  - `deletable_<resource>` — function-scoped, provisions a per-test resource named from `request.node.name` (use for update / delete tests)

Fixtures should be defined in `tests/unit/conftest.py` or before the test functions in the same file.

## Test Organization

```
tests/unit/plugins/<plugin_type>/
  <plugin_family>/
    <plugin_name>/
      test_<plugin_name>_<plugin_type>.py
      test_<plugin_name>_<plugin_type>_int.py
```
