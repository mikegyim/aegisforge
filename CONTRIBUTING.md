# Contributing

Thanks for your interest in AegisForge. This is a portfolio / research project,
but pull requests are welcome.

## Development setup

```bash
git clone https://github.com/mikegyim/aegisforge
cd aegisforge/apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

For the frontend:

```bash
cd apps/frontend
npm install
npm run dev   # proxies /api to http://localhost:8000
```

## Conventions

- Code style: `ruff check`, `ruff format`.
- Tests: `pytest -q` with coverage. New code must include tests.
- Commits: imperative mood ("Add ...", "Fix ..."). Reference an issue if relevant.
- Branches: short-lived feature branches off `main`. Open a PR early.

## Adding a new agent

1. Subclass `BaseAgent` in `apps/api/src/aegisforge/agents.py`.
2. Add it to `AgentRouter`'s default list.
3. Add a focused unit test in `tests/test_agents.py`.
4. Update the README architecture diagram if the new agent introduces a new
   responsibility lane.

## Adding a new LLM provider

1. Subclass `LLMProvider` in `apps/api/src/aegisforge/llm.py`.
2. Add a case to `build_provider`.
3. Add a test that monkeypatches the SDK to assert the prompt-shape contract.
