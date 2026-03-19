"""BenchTask and related Pydantic v2 models for benchmark task definitions."""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel


class StateAssertion(BaseModel):
    """A single assertion about expected state after task execution."""

    field: str
    value: Any | None = None
    contains: str | list[str] | None = None
    not_value: Any | None = None


class ScoringConfig(BaseModel):
    """Per-task scoring weight configuration."""

    outcome: float = 0.6
    efficiency: float = 0.2
    recovery: float = 0.2
    memory_utilization: float = 0.0
    preference_adherence: float = 0.0
    tone_appropriateness: float = 0.0
    boundary_adherence: float = 0.0
    cross_platform_consistency: float = 0.0


class BenchTask(BaseModel):
    """A single benchmark task loaded from YAML."""

    id: str
    title: str
    difficulty: Literal["easy", "medium", "hard", "adversarial"]
    category: str
    description: str
    tools_provided: list[str]
    initial_state: dict
    expected_state: dict
    scoring: ScoringConfig = ScoringConfig()
    max_turns: int
    optimal_commands: int = 1
    timeout_seconds: int = 300
    persona: str | None = None
    memory_required: list[str] | None = None
    todo_category: str | None = None
    expected_agent_behavior: str | None = None
    tone_sensitive: bool = False
    tone_recipient: str | None = None
    tone_context: str | None = None
    personas_applicable: list[str] | None = None

    @classmethod
    def from_yaml(cls, path: Path) -> "BenchTask":
        """Load a BenchTask from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
