# Contributing to CNS

Thank you for your interest in contributing to CNS (Cognition-Native Store)!

## Getting Started

1. **Fork and clone** the repository
2. **Set up your development environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -e ".[dev]"
   pre-commit install
   ```
3. **Start the infrastructure**:
   ```bash
   make up
   python -m cns_py.storage.db --init
   ```

## Development Workflow

### Before committing

1. **Run tests**: `make test`
2. **Run verification**: `make verify` (lint, format, typecheck, tests)
3. **Pre-commit hooks** will auto-run on `git commit`

### Code style

- **Python**: Follow PEP 8; enforced by `ruff` and `black`
- **Line length**: 100 characters
- **Type hints**: Required (checked by `mypy --strict`)
- **Imports**: Sorted by `ruff`

### Testing

- **Unit tests**: Place in `tests/test_*.py`
- **Golden tests**: Add expected outputs to `tests/golden/*.json`
- **Integration tests**: Use `testcontainers` for DB-dependent tests
- **pgTAP**: SQL schema tests in `tests_pg/*.sql`

### Documentation

- **ADRs**: Architectural decisions go in `docs/adr/NNNN-title.md`
- **API changes**: Update relevant docs in `docs/`
- **Comments**: Explain *why*, not *what*

## Pull Request Process

1. **Create a feature branch**: `git checkout -b feature/your-feature-name`
2. **Make your changes** with clear, atomic commits
3. **Update tests** to cover new functionality
4. **Update documentation** if you change APIs or behavior
5. **Ensure CI passes**: All checks must be green
6. **Submit PR** with:
   - Clear description of changes
   - Link to related issues
   - Screenshots/examples if applicable

## Commit Message Format

```
<type>: <short summary>

<optional body>

<optional footer>
```

**Types**: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`

Example:
```
feat: add contradiction detection module

Implements simple subject/predicate clash detection for Phase 4.
Includes unit tests and integration with belief updater.

Closes #42
```

## Code Review

- Be respectful and constructive
- Focus on code quality, not personal preferences
- Respond to feedback promptly
- Approve only when all concerns are addressed

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for design questions
- Check existing issues before creating new ones

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
