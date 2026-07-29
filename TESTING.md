# Testing cloudera.services

The project has rallied around using `pytest` for most everything within the collection, including _integration_ tests.

## Environment Variables

To run integration tests, set the following environment variables.

_For Cloudera SQL Streams Builder_

- `SSB_SSE_API_URL`
- `SSB_SSE_API_USERNAME`
- `SSB_SSE_API_PASSWORD`
- `SSB_SSE_API_KEYTAB_FILE`
- `SMM_KAFKA_BROKERS`
- `SMM_KAFKA_USERNAME`
- `SMM_KAFKA_PASSWORD`
- `SMM_KAFKA_SSL_CAFILE`
- `SMM_SCHEMA_REGISTRY_URL`

_For Apache Ranger_

- `RANGER_ADMIN_URL`
- `RANGER_ADMIN_USERNAME`
- `RANGER_ADMIN_PASSWORD`

_For Cloudera AI_

- `CML_ENDPOINT`
- `CML_API_KEY`


Integration tests use the `env_context` fixture to gate the associated fixture finalizations to check for required environment variables.

> [!IMPORTANT]
> Make sure `PYTHONPATH` is set properly in order to find the nested Ansible imports, i.e. `ansible_collections.namespace.collection.plugins.modules`.

## Hatch

`hatch` is configured to run tests via a matrix of Python vs. Ansible versions.

**Run all regular tests in the first (default) test environment.**

```bash
hatch test
```

**Run selected, regular tests in the default test environment.**

```bash
hatch test -k ssb_project
```

**Run selected, _marked_ tests in the default test environment.**

```bash
hatch test -k ssb_project -m slow
```

**Run _all_ selected tests in the default test environment.**

```bash
hatch test -k ssb_project -m all
```

**Run all tests in all test environments, i.e. matrix of testing environments.**

```bash
hatch test --all -m all
```

> [!WARNING] Testing Python 3.9
> Hatch currently has a dependency (`coverage[toml]`) that conflicts with Python 3.9. To test Python 3.9, run `pytest` in a standalone virtual environment. For example:

```bash
python3.9 -m venv cloudera-services-python3.9
```

Activate this virtual environment, and install the minimal requirements for testing.

```bash
pip install pytest pytest-mock ansible-core==2.15
pip install -r requirements.txt
```

Then run `pytest` directly instead of `hatch test`.

All other requirements, like `PYTHONPATH`, are still valid.

## Custom Pytest Markers

| Marker | Enabled | Description |
| --- | --- | --- |
| `slow` | `False` | Marks tests as slow tests |
| `data_service` | `False` | Marks tests that require an existing Data Service environment (or will create one) |
| `all` | `False` | Marks all tests to run (slow, data_service, and standard) |

By default, only tests _not_ marked with `slow` or `data_service` are executed.

**Run only the slow tests**

```bash
hatch test -m slow
```

**Run only the tests requiring a Data Service fixture**

```bash
hatch test -m data_service
```

**Run only slow and Data Service fixture tests**

```bash
hatch test -m "slow or data_service"
```

**Run all tests**

```bash
hatch test -m all
```
