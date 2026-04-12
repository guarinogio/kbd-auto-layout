# Contributing

Thanks for your interest in improving `kbd-auto-layout`.

## Setup

```bash
git clone https://github.com/guarinogio/kbd-auto-layout.git
cd kbd-auto-layout

python -m venv ~/.venvs/kbd-auto-layout
source ~/.venvs/kbd-auto-layout/bin/activate
pip install -e ".[dev]"
```

## Development workflow

```bash
make format
make lint
make test
```

## Code style

- Use `ruff` for linting and formatting
- Keep functions small and testable
- Prefer explicit behavior over hidden magic
- Preserve CLI behavior unless there is a strong reason to change it

## Testing

Add tests for behavior changes when applicable.

```bash
pytest
```

## Packaging

When touching packaging, verify the Debian build:

```bash
debuild -us -uc
```

## Commits

Conventional-style commit prefixes are preferred:

- `feat:`
- `fix:`
- `docs:`
- `chore:`
- `refactor:`
- `test:`
- `packaging:`
- `ci:`

## Pull Requests

- Keep PRs focused
- Explain what changed and why
- Update docs when needed
- Update tests when needed
- Make sure CI passes
