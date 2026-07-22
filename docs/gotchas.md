> Part of the cloudera.services agent guide — see [AGENTS.md](../AGENTS.md).

# Common Gotchas

1. **`AutoExecuteMeta` metaclass**: Modules with `ServicesModule` base auto-execute `process()` after `__init__` — no explicit `main()` call needed
2. **NULLABLE vs None**: Use `NULLABLE` for unset optional fields, `None` for explicitly null values
3. **Immutable fields**: Validate immutable fields don't change; fail with clear message if they do
4. **RST docs are generated**: Never edit `docsbuild/rst/*.rst` files directly — they're auto-generated from module DOCUMENTATION strings
5. **Collection path**: For `ansible-doc` and doc building, collection must be in `ANSIBLE_COLLECTIONS_PATHS`
6. **Integration tests**: Need environment variables for service endpoints — tests will be skipped if not set via the `env_context` fixture
7. **Pre-commit hooks**: Run automatically on commit — use `hatch run lint` to run manually on all files
8. **Doc-fragment merge order**: earlier-listed fragment wins per sub-key; no duplicate-option error. List the authoritative fragment first (see [documentation.md](documentation.md))
9. **Pagination termination**: a continuation token that is *present but empty/`None`* must terminate the loop — test both "token present" **and** "has a value", or `@paginated` spins forever
10. **Test basename collisions**: unique basenames required (prepend import mode, no `__init__.py`)
11. **Check-mode return values vary by module**: SSB modules return `{}` in check-mode; `ml_project` returns the *intended* resource dict. Assert `changed` + verify persistence via the client, rather than assuming an empty return
