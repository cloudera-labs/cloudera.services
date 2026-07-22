# Cloudera Runtime Collection - Development Guidelines

This is an Ansible collection for Cloudera Data Platform (CDP) Public and Private Cloud services. See [README.md](README.md) for overview and [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow.

This file is a **router**: the invariants below apply to all work; read the linked topic doc for the area you're touching rather than loading everything up front.

## Critical rules (always apply)

- Use **pytest**, never `ansible-test` — for unit *and* integration tests. See [docs/testing.md](docs/testing.md).
- Python via **Hatch (uv-backed)**; Ansible in a **per-project venv**. No global installs.
- Small, reviewable diffs; write the failing test first (TDD).
- **Never edit generated `docsbuild/rst/*.rst`** — regenerate from module docstrings (`hatch run docs:build`).
- `NULLABLE` = unset, `None` = explicitly null. Don't conflate them.
- `ServicesModule` subclasses auto-run `process()` (`AutoExecuteMeta`) — no manual `main()` call.

## Quick start commands

**Setup environment:**
```bash
pip install hatch
hatch shell  # Activates default environment with all dependencies
pre-commit install
```

**Run tests:**
```bash
pytest tests/unit/  # Unit and integration tests (integration tests require env vars)
hatch test  # Runs tests on first compatible environment of the hatch matrix
hatch -a test  # Run tests on all environments in the hatch matrix (sequentially)
```

**Build:**
```bash
hatch run lint  # Lint and format
ansible-galaxy collection build
hatch run docs:build  # Generate API docs
```

## Guide map

| Topic | Read this when… | File |
|---|---|---|
| Architecture | adding/changing a module's base class, HTTP client, data model, or state handling | [docs/architecture.md](docs/architecture.md) |
| Authentication | wiring auth/transport, adding a service's credentials, or touching ML/Ranger auth | [docs/authentication.md](docs/authentication.md) |
| Authoring modules | creating a new module — naming, scaffolding template, end-to-end workflow | [docs/modules.md](docs/modules.md) |
| Documentation | writing DOCUMENTATION/EXAMPLES/RETURN or doc fragments | [docs/documentation.md](docs/documentation.md) |
| Testing | writing unit or integration tests, fixtures, test layout | [docs/testing.md](docs/testing.md) |
| Gotchas | quick check before you commit; debugging surprising behavior | [docs/gotchas.md](docs/gotchas.md) |

## Resources

- **API docs**: Run `hatch run docs:build` then open `docsbuild/build/html/index.html`
- **Testing guide**: [TESTING.md](TESTING.md) (integration env vars); `tests/unit/conftest.py` (fixtures/utilities)
- **Module examples**: Check `plugins/modules/ssb_*.py` for modern architecture patterns
- **Hatch commands**: Run `hatch env show` to see available environments and scripts
