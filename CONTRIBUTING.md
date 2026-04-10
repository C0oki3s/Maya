# Contributing to Maya

Thank you for your interest in contributing to Maya! This guide will help you get started.

## Code of Conduct

By participating in this project, you agree to uphold our [Code of Conduct](CODE_OF_CONDUCT.md). Please report unacceptable behavior to the maintainers.

## Getting Started

### Development Setup

```bash
git clone https://github.com/USER/MOBSEC.git
cd MOBSEC
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### Running Tests

```bash
# All tests (except device-gated integration)
pytest -q -k "not integration"

# Full suite (requires connected device)
pytest -q
```

### Linting

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
pip install ruff
ruff check .
ruff format .
```

## How to Contribute

### Reporting Bugs

1. Check existing [issues](https://github.com/USER/MOBSEC/issues) to avoid duplicates
2. Open a new issue using the **Bug Report** template
3. Include: steps to reproduce, expected vs actual behavior, environment details

### Suggesting Features

1. Open an issue using the **Feature Request** template
2. Describe the use case, not just the solution

### Submitting Pull Requests

1. **Fork** the repository and create a branch from `main`
2. **Name your branch** descriptively: `feat/frida-gadget-tool`, `fix/checkpoint-resume`, `docs/skill-guide`
3. **Write code** following the conventions below
4. **Add tests** for new functionality
5. **Run tests** locally: `pytest -q`
6. **Run linter**: `ruff check . && ruff format --check .`
7. **Open a PR** against `main` with a clear description

### PR Review Process

All PRs require:
- **1 approving review** from a maintainer
- **Passing CI** (lint, tests, Docker build check)
- **CodeQL** security scan with no new alerts
- **No merge conflicts** with `main`

Maintainers will review within 48 hours. Expect feedback — this is a security tool and code quality is critical.

## Code Conventions

### Tools

- Always use `@register_tool(sandbox_execution=True|False)`
- Return `dict` from every tool — `{"status": "ok", ...}` or `{"error": "msg"}`
- Never raise exceptions — catch and return `{"error": str(exc)}`
- Include a docstring (becomes XML schema description)
- Add `agent_state: AgentState | None = None` if the tool needs state access
- Use `subprocess.run()` with `capture_output=True` and `timeout=`
- Import every new tool module in `maya/tools/__init__.py`

### Agents

- Subclass `BaseAgent`
- Implement `build_system_prompt()` and `on_scan_complete()`
- Use `@dataclass(slots=True)` for data classes

### Skills

- Place in the correct category: `vulnerabilities/`, `tools/`, `frameworks/`, `platforms/`, `agents/`, `coordination/`
- Include YAML frontmatter with `name`, `description`, `category`, `applies_to`
- Use `requires` field for skill dependencies

### General

- Async-first (`asyncio`, not threading)
- Type hints on all function signatures
- No hardcoded credentials or API keys — use env vars or config files

## Adding a New Tool

1. Create `maya/tools/my_new_tool.py`
2. Use the `@register_tool` decorator
3. Import in `maya/tools/__init__.py`
4. Add corresponding skill in `maya/skills/tools/my_tool_operations.md`
5. Write tests in `tests/test_my_new_tool.py`
6. Submit PR

## Adding a New Skill

1. Create `maya/skills/<category>/my_skill.md` with YAML frontmatter
2. Test loading: `maya --list-skills`
3. Submit PR

## Release Process

Releases are tagged on `main` with semver (`v0.2.0`, `v1.0.0`). Pushing a tag triggers:
1. CI runs full test suite
2. Docker image is built and published to `ghcr.io`
3. GitHub Release is created with auto-generated notes and SBOM

## Questions?

Open a [Discussion](https://github.com/USER/MOBSEC/discussions) or reach out to the maintainers.
