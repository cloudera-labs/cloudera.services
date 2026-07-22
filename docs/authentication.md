> Part of the cloudera.services agent guide — see [AGENTS.md](../AGENTS.md).

# Authentication

## Custom Auth / Transport (mixin + client subclass)

When a service needs non-standard auth (e.g. CML's `Authorization: Bearer <api_key>`), split the
work across three seams — do **not** subclass `AnsibleModule` or hand-roll `requests`:

1. **Parameter mixin** — a `ParametersMixin` subclass declares the auth params and env fallbacks.
   `ServicesModule.__init__` auto-merges its `get_argument_spec()` and calls `init_parameters()`.
   Re-declaring a base param here (e.g. `url`) overrides it, since the mixin merge runs *after* the
   base merge.
2. **Client subclass** — an `AnsibleServicesClient` subclass owns the transport, reading
   `module.params[...]` and injecting headers. A mixin alone can't do this: `init_parameters` runs
   *before* `api_client` is built.
3. **Factory hook** — override `build_api_client()` on the module base to return the subclass.
   Default (`common.py`) returns a plain `AnsibleServicesClient`, so SSB is unaffected.

```python
class CmlServicesClient(AnsibleServicesClient):          # transport: Bearer header
    def __init__(self, module, **kwargs):
        api_key = module.params.get("api_key")
        headers = dict(kwargs.pop("headers", {}))
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        super().__init__(module=module, headers=headers, **kwargs)

class CmlAuthMixin(ParametersMixin):                     # params: api_key + CML url fallback
    @staticmethod
    def get_argument_spec():
        return dict(api_key=..., url=...)

class MlServicesModule(ServicesModule, CmlAuthMixin):    # wiring: reused by all ml_* modules
    def build_api_client(self):
        return CmlServicesClient(module=self.module, ...)
```

Reference implementation: `plugins/module_utils/ml.py` (`ml_project` is migrated to this pattern).

## Per-service auth patterns

**Modern modules (ServicesModule):**
- Parameters: `url`/`endpoint`, `url_username`, `url_password`
- Optional: `client_cert`, `client_key`, `validate_certs`

**ML modules (CML):**
- `url` (aliases `endpoint`/`endpoint_url`/`workspace_url`) + `api_key` (alias `token`) — Bearer-token auth
- Environment fallbacks: `CML_ENDPOINT` (url), `CML_API_KEY` (api_key)
- Auth wired via `CmlAuthMixin` + `CmlServicesClient` + `MlServicesModule.build_api_client()` (see Custom Auth / Transport above)
- Shared option docs live in the `cloudera.services.ml_client` doc fragment
- **Migration state:** `ml_project` is on the modern service model (`MlServicesModule`); the other 15 `ml_*` modules + `ml_v1.py` are still legacy (`MLModule`) and unmigrated — their test collection stays red until migrated

**Ranger modules:**
- `endpoint` + `username` + `password`
- Uses `apache-ranger` Python client
- Legacy, migrate to modern architecture
