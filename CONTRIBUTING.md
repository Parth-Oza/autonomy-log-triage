# Contributing

Contributions that improve correctness, documentation, synthetic examples, or test coverage are welcome.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Change requirements

- Keep runtime dependencies at zero unless a change clearly justifies one.
- Add tests for new event types, validation rules, or report fields.
- Preserve deterministic ordering and stable JSON output.
- Use synthetic examples only; never submit proprietary logs or schemas.
- Update the README and architecture notes when behavior or contracts change.

Open a focused pull request explaining the problem, the chosen behavior, and how it was verified.
