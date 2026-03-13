# Contributing to KLIK-Bench

Thank you for your interest in contributing to KLIK-Bench. This document provides guidelines for contributing to the benchmark.

## Development Setup

```bash
git clone https://github.com/minervacap2022/KLIK-Bench.git
cd KLIK-Bench
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest tests/ -v --tb=short
```

## Adding a New Task

1. Create a YAML file in `data/tasks/` following the schema in existing tasks
2. Assign the task to one or more personas via the `persona` field
3. Define `memory_required` fields that reference persona memory paths
4. Set appropriate `scoring` weights (include `memory_utilization`, `preference_adherence`, `tone_appropriateness` for KLIK-specific evaluation)
5. Run the full test suite to validate

## Adding a New Persona

1. Create a YAML file in `data/personas/` following the schema in existing personas
2. Include: `preferences`, `user_facts`, `entity_graph` (people, projects, organizations), and `session_history`
3. Update `data/metadata.yaml` with the new persona entry
4. Add tests in `tests/unit/test_persona.py`

## Adding a New Mock Backend

1. Create `klik_bench/mock_backends/<name>.py` subclassing `BaseMockBackend`
2. Implement `route_command()` to handle CLI commands
3. Create corresponding YAML tool adapter in `klik_bench/tool_adapters/<name>.yaml`
4. Add tests in `tests/unit/test_mock_<name>.py`
5. Register the backend in `klik_bench/harness/benchmark.py`

## Code Style

- Python 3.12+
- Type hints on all public functions
- Pydantic v2 for data models, dataclasses for lightweight runtime types
- Async/await for I/O operations
- Tests required for all new code

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request with a clear description

## License

By contributing, you agree that your contributions will be licensed under the Apache-2.0 License.
