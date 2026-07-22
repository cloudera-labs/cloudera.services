> Part of the cloudera.services agent guide — see [AGENTS.md](../AGENTS.md).

# Documentation Standards

## Doc Fragments

Use `extends_documentation_fragment: cloudera.services.services_client` for:
- Standard HTTP client parameters (url/endpoint, username, password, certs)
- Avoids duplicating common parameter docs

Create new fragments in `plugins/doc_fragments/` for shared parameter groups for a module as needed.

**Fragment merge order matters.** `ansible.utils.plugin_docs.merge_fragment` does a shallow
per-sub-key merge where the **earlier-listed fragment wins**; there is no duplicate-option error.
So when two fragments both document the same option (e.g. `url` in both `ml_client` and
`services_client`), list the fragment whose version should win **first**, and have it fully restate
the option (aliases, fallback, etc.) — not just the delta:

```yaml
extends_documentation_fragment:
  - cloudera.services.ml_client        # first: owns the full url + api_key
  - cloudera.services.services_client  # supplies timeout/page_size/validate_certs/proxy/etc.
```

## DOCUMENTATION Block

- Include all parameters from `argument_spec`
- Specify accurate types: `str`, `int`, `bool`, `list`, `dict`, `path`
- Add `required: true/false` and `default:` values
- Use `choices:` for enums
- Mark deprecated params appropriately

## EXAMPLES Block

- Use variables for credentials: `{{ endpoint }}`, `{{ username }}`
- Show 2-4 common use cases (not exhaustive)
- Include task names that explain purpose
- Show state transitions (present/absent) where applicable

## RETURN Block

- Document all module return values
- Specify `returned:` condition (always, on success, when changed, etc.)
- Include nested structure for dicts with `contains:`

## Validation

After updating module docs:
```bash
ansible-doc -t module cloudera.services.module_name  # Validate parsing
hatch run docs:build  # Regenerate RST docs
```
