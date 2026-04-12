# Contributing

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
- Prefer explicit behavior over magic

## Testing

All changes must include tests when applicable.

```bash
pytest
```

## Commits

Use conventional commits when possible:

- feat:
- fix:
- docs:
- chore:
- refactor:

## Pull Requests

- Keep PRs focused
- Include description and context
- Ensure CI passes
