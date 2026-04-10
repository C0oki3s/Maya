## Description

<!-- What does this PR do? Why is it needed? -->

## Type of Change

- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] New tool (`@register_tool` function)
- [ ] New skill (Markdown knowledge pack)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] CI/Infrastructure change

## How Has This Been Tested?

<!-- Describe the tests you ran. Include relevant details. -->

- [ ] `pytest -q` passes locally
- [ ] `ruff check .` passes
- [ ] `ruff format --check .` passes
- [ ] Docker build succeeds (if touching containers/ or maya/)
- [ ] Tested on connected device (if applicable)

## Checklist

- [ ] My code follows the project's [conventions](CONTRIBUTING.md#code-conventions)
- [ ] I have added tests for new functionality
- [ ] New tools return `dict` and never raise exceptions
- [ ] New tools are imported in `maya/tools/__init__.py`
- [ ] New skills have YAML frontmatter with required fields
- [ ] I have updated documentation if needed
- [ ] My changes generate no new linter warnings
