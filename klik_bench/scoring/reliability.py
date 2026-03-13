"""Reliability metrics for AI agent evaluation.

Implements scientific metrics from recent agent reliability research:
- Cronbach's alpha for internal consistency across runs
- McDonald's omega for composite reliability
- CLEAR framework dimensions (Cost, Latency, Efficacy, Assurance, Reliability)
- Pass@k consistency metrics from tau-bench

References:
- "Towards a Science of AI Agent Reliability" (arXiv:2602.16666)
- "Beyond Accuracy: A Multi-Dimensional Framework for Evaluating Enterprise Agentic AI Systems"
- tau-bench (Sierra Research, 2024)
"""

from dataclasses import dataclass
from typing import Any
import statistics


@dataclass
class ReliabilityMetrics:
    """Comprehensive reliability analysis result."""

    # Internal consistency (Cronbach's alpha)
    cronbachs_alpha: float

    # Pass@k scores
    pass_at_1: float
    pass_at_3: float
    pass_at_5: float

    # Outcome consistency (std dev across runs)
    outcome_variance: float
    outcome_std: float

    # Run-to-run correlation
    run_correlation: float

    # Production readiness flag (alpha >= 0.80)
    production_ready: bool

    # Individual run scores for analysis
    run_scores: list[float]


@dataclass
class CLEARMetrics:
    """CLEAR framework metrics for enterprise deployment evaluation.

    Based on "Beyond Accuracy" framework for enterprise agentic AI.
    """

    # Cost: API cost per successful task completion
    cost_per_success: float

    # Latency: Average time to completion
    latency_mean: float
    latency_p95: float

    # Efficacy: Task success rate (outcome >= 0.5)
    efficacy: float

    # Assurance: Confidence in predictions (based on consistency)
    assurance: float

    # Reliability: pass@k and consistency combined
    reliability: float


def compute_cronbachs_alpha(run_scores: list[list[float]]) -> float:
    """Compute Cronbach's alpha for internal consistency.

    Args:
        run_scores: List of score lists, where each inner list contains
                   scores from one item (task) across k runs.
                   Shape: [n_tasks, k_runs]

    Returns:
        Cronbach's alpha coefficient (0-1, higher is more consistent).
        Values >= 0.80 indicate production readiness.

    Formula:
        alpha = (k / (k-1)) * (1 - sum(var_i) / var_total)
    """
    if not run_scores or len(run_scores) < 2:
        return 0.0

    k = len(run_scores[0])  # Number of runs
    if k < 2:
        return 0.0

    # Compute variance for each item (task) across runs
    item_variances = []
    for scores in run_scores:
        if len(scores) >= 2:
            item_variances.append(statistics.variance(scores))
        else:
            item_variances.append(0.0)

    sum_item_variance = sum(item_variances)

    # Compute total variance (sum of all scores across all items)
    total_scores_per_run = []
    for run_idx in range(k):
        run_total = sum(scores[run_idx] for scores in run_scores if run_idx < len(scores))
        total_scores_per_run.append(run_total)

    if len(total_scores_per_run) < 2:
        return 0.0

    total_variance = statistics.variance(total_scores_per_run)

    if total_variance == 0:
        return 1.0  # Perfect consistency

    alpha = (k / (k - 1)) * (1 - sum_item_variance / total_variance)
    return max(0.0, min(1.0, alpha))


def compute_pass_at_k(
    run_outcomes: list[list[float]],
    threshold: float = 0.5,
    k: int = 5
) -> float:
    """Compute pass@k metric from tau-bench.

    A task passes only if ALL k runs achieve outcome >= threshold.

    Args:
        run_outcomes: List of outcome scores per task, shape [n_tasks, n_runs]
        threshold: Minimum outcome score to count as success
        k: Number of runs to require success on

    Returns:
        Fraction of tasks that pass on all k runs.
    """
    if not run_outcomes:
        return 0.0

    passing_tasks = 0
    for task_runs in run_outcomes:
        # Take first k runs (or all if fewer)
        runs_to_check = task_runs[:k]
        if len(runs_to_check) >= k and all(score >= threshold for score in runs_to_check):
            passing_tasks += 1

    return passing_tasks / len(run_outcomes)


def compute_outcome_consistency(run_scores: list[list[float]]) -> tuple[float, float]:
    """Compute outcome consistency metrics.

    Returns:
        (variance, std_dev) across runs for each task, averaged.
    """
    if not run_scores:
        return 0.0, 0.0

    variances = []
    for scores in run_scores:
        if len(scores) >= 2:
            variances.append(statistics.variance(scores))

    if not variances:
        return 0.0, 0.0

    mean_variance = statistics.mean(variances)
    mean_std = mean_variance ** 0.5

    return mean_variance, mean_std


def analyze_reliability(
    run_outcomes: list[list[float]],
    costs: list[float] | None = None,
    latencies: list[float] | None = None,
) -> ReliabilityMetrics:
    """Comprehensive reliability analysis for a set of task runs.

    Args:
        run_outcomes: Outcome scores, shape [n_tasks, k_runs]
        costs: Optional cost per task (for CLEAR metrics)
        latencies: Optional latency per task (for CLEAR metrics)

    Returns:
        ReliabilityMetrics with all computed values.
    """
    all_scores = [score for task_runs in run_outcomes for score in task_runs]

    alpha = compute_cronbachs_alpha(run_outcomes)
    pass_1 = compute_pass_at_k(run_outcomes, k=1)
    pass_3 = compute_pass_at_k(run_outcomes, k=3)
    pass_5 = compute_pass_at_k(run_outcomes, k=5)
    variance, std = compute_outcome_consistency(run_outcomes)

    # Run correlation: average correlation between consecutive runs
    # Simplified: we use the variance as a proxy (lower variance = higher correlation)
    run_correlation = max(0.0, 1.0 - std)

    return ReliabilityMetrics(
        cronbachs_alpha=alpha,
        pass_at_1=pass_1,
        pass_at_3=pass_3,
        pass_at_5=pass_5,
        outcome_variance=variance,
        outcome_std=std,
        run_correlation=run_correlation,
        production_ready=alpha >= 0.80,
        run_scores=all_scores,
    )


def compute_clear_metrics(
    run_outcomes: list[list[float]],
    costs: list[float],
    latencies: list[float],
    threshold: float = 0.5,
) -> CLEARMetrics:
    """Compute CLEAR framework metrics for enterprise evaluation.

    Args:
        run_outcomes: Outcome scores, shape [n_tasks, k_runs]
        costs: API cost per task
        latencies: Time to completion per task (seconds)
        threshold: Success threshold

    Returns:
        CLEARMetrics for enterprise deployment assessment.
    """
    # Efficacy: fraction of runs with outcome >= threshold
    all_outcomes = [score for task_runs in run_outcomes for score in task_runs]
    efficacy = sum(1 for s in all_outcomes if s >= threshold) / len(all_outcomes) if all_outcomes else 0.0

    # Cost per success
    successful_costs = [
        c for c, scores in zip(costs, run_outcomes)
        if any(s >= threshold for s in scores)
    ]
    cost_per_success = statistics.mean(successful_costs) if successful_costs else float('inf')

    # Latency
    latency_mean = statistics.mean(latencies) if latencies else 0.0
    sorted_latencies = sorted(latencies) if latencies else [0.0]
    p95_idx = int(len(sorted_latencies) * 0.95)
    latency_p95 = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]

    # Assurance: based on outcome consistency (lower std = higher assurance)
    _, std = compute_outcome_consistency(run_outcomes)
    assurance = max(0.0, 1.0 - std)

    # Reliability: combination of pass@k and consistency
    reliability_metrics = analyze_reliability(run_outcomes)
    reliability = (reliability_metrics.pass_at_5 + reliability_metrics.cronbachs_alpha) / 2

    return CLEARMetrics(
        cost_per_success=cost_per_success,
        latency_mean=latency_mean,
        latency_p95=latency_p95,
        efficacy=efficacy,
        assurance=assurance,
        reliability=reliability,
    )


def format_reliability_report(metrics: ReliabilityMetrics, clear: CLEARMetrics | None = None) -> str:
    """Format reliability metrics as a human-readable report."""
    lines = [
        "=" * 60,
        "RELIABILITY ANALYSIS REPORT",
        "=" * 60,
        "",
        "Internal Consistency:",
        f"  Cronbach's Alpha:     {metrics.cronbachs_alpha:.3f} {'[PRODUCTION READY]' if metrics.production_ready else '[BELOW THRESHOLD]'}",
        f"  Run-to-Run Correlation: {metrics.run_correlation:.3f}",
        "",
        "Pass@k Metrics (tau-bench style):",
        f"  pass@1: {metrics.pass_at_1:.1%}",
        f"  pass@3: {metrics.pass_at_3:.1%}",
        f"  pass@5: {metrics.pass_at_5:.1%}",
        f"  Degradation (1→5): {(metrics.pass_at_1 - metrics.pass_at_5) / metrics.pass_at_1 * 100:.1f}%" if metrics.pass_at_1 > 0 else "  Degradation: N/A",
        "",
        "Outcome Consistency:",
        f"  Variance: {metrics.outcome_variance:.4f}",
        f"  Std Dev:  {metrics.outcome_std:.4f}",
    ]

    if clear:
        lines.extend([
            "",
            "CLEAR Framework (Enterprise Readiness):",
            f"  Cost per Success:  ${clear.cost_per_success:.4f}",
            f"  Latency (mean):    {clear.latency_mean:.2f}s",
            f"  Latency (p95):     {clear.latency_p95:.2f}s",
            f"  Efficacy:          {clear.efficacy:.1%}",
            f"  Assurance:         {clear.assurance:.1%}",
            f"  Reliability:       {clear.reliability:.1%}",
        ])

    lines.extend(["", "=" * 60])
    return "\n".join(lines)
