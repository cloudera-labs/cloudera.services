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

**Atlas fixtures** (`tests/unit/conftest.py`):
- `atlas_typedef_client` is a module-scoped `AtlasTypeDefClient`; `atlas_purge_typedef(name)` registers a typedef name for deletion at teardown and returns the name
- `atlas_existing_enum_def` and `atlas_deletable_{enum,classification,entity,struct,relationship,business_metadata}_def` follow the `existing_`/`deletable_` pattern above
- `atlas_relationship_end_types` creates the two entity types a relationship connects; list it before `atlas_purge_typedef` in a test so a registered relationship is deleted before the types it references
- Build names with `_atlas_type_name(prefix, raw)`, which gives `ansible_test_<prefix>_<test name>` using only letters, digits and underscores
- `atlas_purge_typedef(name, force=False)` deletes in registration order, so register a type that references others before the types it references. Pass `force=True` for business metadata, which Atlas will not delete otherwise
- Module integration tests define their own `atlas_module_args` fixture, mapping `ATLAS_API_*` onto the module's connection arguments
- A new simple `atlas_deletable_<category>_def` fixture calls `_create_deletable(client, purge, create, typedef, force=False)`, which clears any leftover, creates the typedef and registers it for purge. Relationship stays explicit because it also depends on `atlas_relationship_end_types`. `_safe_delete(client, name, force=False)` is the teardown delete that warns instead of failing the test

**Atlas entity fixtures** (`tests/unit/conftest.py`): `atlas_entity_client` is a module-scoped `AtlasEntityClient`. `atlas_entity_type` provides a custom entity type (extending `Referenceable`, so `qualifiedName` is unique); it is created if absent and removed at teardown only when the fixture created it. `atlas_deletable_entity` creates a uniquely named entity of that type, and `atlas_purge_entity(guid)` registers a guid for cleanup. Atlas deletes softly and refuses to delete a type that still has soft-deleted instances, so teardown deletes each entity and then purges it (purging needs Atlas administrator rights; a refusal only warns). Integration tests create their own entities of the throwaway type and never touch hook-owned types such as `hive_table`.

**Atlas HTTP stubs** (`tests/unit/__init__.py`, imported from `ansible_collections.cloudera.services.tests.unit`): to test a module's Atlas error paths without a server, patch `FETCH_URL` with a `side_effect` that returns `http_result(mocker, status, body)` per HTTP method, and use `atlas_error_result(mocker)` for an HTTP 400 carrying `ATLAS_ERROR_MESSAGE`. Don't copy these into individual test files.

## Test Organization

```
tests/unit/plugins/<plugin_type>/
  <plugin_family>/
    <plugin_name>/
      test_<plugin_name>_<plugin_type>.py
      test_<plugin_name>_<plugin_type>_int.py
```
