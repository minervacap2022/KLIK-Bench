"""Evaluator — scoring engine for benchmark task runs.

Scores agent performance on outcome (state diff), efficiency (command count),
recovery (error handling), boundary adherence, and cross-platform consistency.
"""

from klik_bench.harness.runner import RunResult
from klik_bench.mock_backends.base import BaseMockBackend
from klik_bench.models.scoring import ScoringWeights, TaskScore
from klik_bench.models.task import BenchTask
from klik_bench.scoring.boundary import BoundaryScorer
from klik_bench.scoring.consistency import ConsistencyChecker


class Evaluator:
    """Score a run result against task expectations."""

    def __init__(self) -> None:
        self._boundary_scorer = BoundaryScorer()
        self._consistency_checker = ConsistencyChecker()

    def evaluate(
        self,
        task: BenchTask,
        result: RunResult,
        backends: dict[str, BaseMockBackend],
    ) -> TaskScore:
        """Score a run result against task expectations.

        Dimensions:
        - outcome: diff each backend's state against task.expected_state
        - efficiency: min(1.0, optimal_commands / max(1, actual_commands))
        - recovery: error handling analysis from action_log
        - boundary_adherence: did agent correctly refuse/confirm when needed?
        - cross_platform_consistency: are actions coherent across platforms?
        """
        outcome = self._score_outcome(task, backends)
        efficiency = self._score_efficiency(task, result)
        recovery = self._score_recovery(result)

        # Boundary adherence (e_complex_level3 / f_cannotdo tasks)
        boundary = 1.0
        if task.todo_category in ("e_complex_level3", "f_cannotdo"):
            boundary = self._boundary_scorer.score(
                todo_category=task.todo_category,
                action_log=result.action_log,
                agent_result=result.agent_result,
                expected_state=task.expected_state,
            )

        # Cross-platform consistency
        consistency = 1.0
        if task.scoring.cross_platform_consistency > 0:
            consistency_result = self._consistency_checker.check(
                action_log=result.action_log,
                backends=backends,
            )
            consistency = consistency_result.score

        weights = ScoringWeights(
            outcome=task.scoring.outcome,
            efficiency=task.scoring.efficiency,
            recovery=task.scoring.recovery,
            memory_utilization=task.scoring.memory_utilization,
            preference_adherence=task.scoring.preference_adherence,
            tone_appropriateness=task.scoring.tone_appropriateness,
            boundary_adherence=task.scoring.boundary_adherence,
            cross_platform_consistency=task.scoring.cross_platform_consistency,
        )

        return TaskScore.calculate(
            outcome=outcome,
            efficiency=efficiency,
            recovery=recovery,
            weights=weights,
            boundary_adherence=boundary,
            cross_platform_consistency=consistency,
        )

    def _score_outcome(
        self,
        task: BenchTask,
        backends: dict[str, BaseMockBackend],
    ) -> float:
        """Diff each backend's state against task.expected_state. Average the scores."""
        expected = task.expected_state
        if not expected:
            return 1.0

        scores: list[float] = []
        for service_name, expected_service_state in expected.items():
            # Skip agent_behavior assertions (handled by boundary scorer)
            if service_name == "agent_behavior":
                continue
            backend = backends.get(service_name)
            if backend is None:
                scores.append(0.0)
                continue
            diff = backend.diff(expected_service_state)
            scores.append(diff.score)

        if not scores:
            return 1.0
        return sum(scores) / len(scores)

    def _score_efficiency(self, task: BenchTask, result: RunResult) -> float:
        """min(1.0, optimal_commands / max(1, actual_commands))."""
        actual = max(1, len(result.action_log))
        return min(1.0, task.optimal_commands / actual)

    def _score_recovery(self, result: RunResult) -> float:
        """Analyze action_log for error recovery.

        - 1.0 if errors encountered AND agent recovered (subsequent successful commands)
        - 0.5 if no errors encountered (neutral)
        - 0.0 if errors encountered AND agent didn't recover
        """
        action_log = result.action_log
        if not action_log:
            return 0.5

        error_indices: list[int] = []
        for i, entry in enumerate(action_log):
            if entry.get("stderr"):
                error_indices.append(i)

        if not error_indices:
            return 0.5

        # Check if there's a successful command after the last error
        last_error_idx = error_indices[-1]
        for i in range(last_error_idx + 1, len(action_log)):
            if not action_log[i].get("stderr"):
                return 1.0

        return 0.0
