# KLIK-Bench: Benchmarking AI Agents on Memory-Grounded Multi-Tool Orchestration

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97-HuggingFace-yellow.svg)](https://huggingface.co/datasets/ChengyiX/KLIK-Bench)
[![arXiv](https://img.shields.io/badge/arXiv-coming%20soon-b31b1b.svg)]()

## Abstract

KLIK-Bench is the first benchmark designed to evaluate AI agents' ability to execute tasks **grounded in user-specific memories, preferences, entity knowledge graphs, and cross-platform context**. Unlike existing agent benchmarks that test generic tool-use proficiency, KLIK-Bench introduces a critical dimension: the same task specification must produce different correct outputs depending on the user persona the agent is acting on behalf of.

Consider a simple directive: "Create a task for the auth migration and notify the team." For an Engineering Lead who uses Linear and Slack, the correct execution involves `linear issue create` followed by `slack message send` to `#platform-team`. For a Product Manager who uses Jira and Microsoft Teams, the identical instruction requires `jira issue create` and `teams message send` to the product channel. An agent that ignores persona context and defaults to any single platform fails the benchmark -- even if the task management operation itself succeeds.

KLIK-Bench evaluates six dimensions that no other benchmark covers in combination: **outcome correctness** (did the task succeed?), **efficiency** (how many actions relative to optimal?), **error recovery** (did the agent handle failures gracefully?), **memory utilization** (did the agent leverage session history and entity relationships?), **preference adherence** (did the agent use the user's preferred tools?), and **tone appropriateness** (was the agent's communication suitable for sensitive recipients?). An additional **cross-platform consistency** metric checks whether entities created on one platform are properly referenced in notifications on another.

## Key Features

- **Persona-grounded evaluation**: 5 distinct user personas with rich entity graphs, session histories, tool preferences, and user facts. The same task yields different correct answers per persona.
- **Memory utilization scoring**: Measures whether agents leverage relevant memories (entity relationships, past meeting decisions, user facts) when executing tasks.
- **LLM-based tone judgment**: Evaluates communication appropriateness when agents send messages to sensitive recipients (e.g., employees experiencing burnout, clients with escalated concerns).
- **Cross-platform consistency checking**: Validates that actions across platforms are coherent -- entities created on one platform should be referenced in notifications on another; reassignments should notify both old and new assignees.
- **Adversarial memory tasks**: Tests agents on scenarios with conflicting information (e.g., a team holiday that conflicts with a meeting request, ambiguous volunteer assignments from meeting transcripts).
- **12 CLI tool adapters**: 7 real-world tools (GitHub, Slack, Linear, Notion, Google Workspace, Jira, Microsoft) and 5 fictional tools for memorization-proof evaluation.
- **Deterministic mock backends**: Stateful service simulators enable fully reproducible evaluation without API costs.
- **Pass^k consistency metric**: Measures reliability across k runs, not just peak performance (adapted from tau-bench).

## Benchmark Statistics

| Dimension | Count |
|-----------|-------|
| Total tasks | 20 |
| Easy tasks | 5 |
| Medium tasks | 8 |
| Hard tasks | 5 |
| Adversarial tasks | 2 |
| Personas | 5 |
| Tool adapters | 12 (7 real + 5 fictional) |
| Mock backends | 7 |
| Scoring dimensions | 7 |

### Task Categories

| Category | Description | Task Count |
|----------|-------------|------------|
| `cross_platform_sync` | Create entities on one platform, notify on another | 4 |
| `memory_grounded` | Tasks requiring session history or entity graph knowledge | 5 |
| `people_communication` | Messages requiring tone sensitivity and relationship awareness | 3 |
| `knowledge_retrieval` | Finding information across platforms using persona context | 2 |
| `preference_sensitive` | Tasks where tool choice depends on user preferences | 2 |
| `multi_session` | Tasks spanning multiple meeting sessions | 1 |
| `adversarial` | Conflicting information or ambiguous scenarios | 2 |
| `composite` | Multi-step tasks combining several categories | 1 |

## Persona System

KLIK-Bench defines 5 user archetypes, each with distinct tool preferences, entity graphs, session histories, and communication patterns:

| Persona | Archetype | Organization | Preferred Tools | Key Testing Dimension |
|---------|-----------|-------------|----------------|----------------------|
| Sarah Chen | Engineering Lead | Nexus Technologies | Linear, Slack, GitHub, Notion | Technical team coordination, PR workflows |
| James Rivera | Product Manager | CloudSync Inc | Jira, Teams, Confluence | Cross-functional communication, sprint management |
| Emily Watson | Sales Director | TechForward | Salesforce, Slack, Google Workspace | Client communication tone, deal tracking |
| Michael Zhang | Founder/CEO | DataVault AI | Linear, Slack, Notion | Strategic decision context, investor relations |
| Aisha Patel | Data Scientist | QuantumMetrics | Jira, Slack, GitHub | Technical documentation, experiment tracking |

Each persona includes:
- **Preferences**: Preferred tools for task management, documentation, communication, file storage, calendar, email, and code
- **User facts**: Personal characteristics and work habits that should influence agent behavior
- **Entity graph**: People (with roles, relationships, and platform handles), projects (with status, priority, and team composition), and organizations
- **Session history**: Past meeting summaries, decisions made, and participants -- providing temporal context for ongoing work

## Installation

```bash
pip install git+https://github.com/minervacap2022/KLIK-Bench.git
```

For development:

```bash
git clone https://github.com/minervacap2022/KLIK-Bench.git
cd KLIK-Bench
pip install -e ".[dev]"
```

## Quick Start

### Run with the dummy agent (baseline)

```bash
python scripts/run_benchmark.py --agent dummy --k 1
```

### Programmatic usage

```python
import asyncio
from pathlib import Path

from klik_bench.agents.dummy import DummyAgent
from klik_bench.harness.benchmark import BenchmarkRunner

async def run():
    runner = BenchmarkRunner(
        tasks_dir=Path("data/tasks"),
        agent=DummyAgent(),
        k=3,
    )
    report = await runner.run_all()
    print(f"Overall score: {report.overall_score:.3f}")
    print(f"Pass^k: {report.overall_pass_k:.3f}")
    for diff, score in report.by_difficulty.items():
        print(f"  {diff}: {score:.3f}")

asyncio.run(run())
```

### Implement a custom agent

```python
from klik_bench.agents.base import BenchAgent
from klik_bench.models.observation import Action, Observation

class MyAgent(BenchAgent):
    async def act(self, observation: Observation) -> Action:
        # observation.task: the task description
        # observation.tools: available tool specifications
        # observation.memory: persona context (preferences, entity graph, etc.)
        # observation.stdout/stderr: output from previous command

        if observation.is_first_turn:
            # Analyze task and memory, decide first action
            return Action.command(["linear", "issue", "create", "--title", "My task"])
        else:
            return Action.finish("Task completed")

    def reset(self) -> None:
        pass  # Reset agent state between runs
```

## Evaluation Metrics

KLIK-Bench evaluates agents across 7 dimensions:

| Metric | Weight (default) | Description |
|--------|---------|-------------|
| **Outcome** | 0.40 | State diff between actual and expected backend states after execution. Scored 0.0--1.0 via recursive deep comparison with partial credit. |
| **Efficiency** | 0.10 | `min(1.0, optimal_commands / actual_commands)`. Rewards agents that solve tasks in fewer steps. |
| **Recovery** | 0.10 | 1.0 if agent encountered errors and recovered; 0.5 if no errors encountered (neutral); 0.0 if errors encountered without recovery. |
| **Memory Utilization** | 0.20 | Fraction of `memory_required` fields (dot-paths into persona context) whose resolved values appear in the agent's action log. |
| **Preference Adherence** | 0.10 | Fraction of tool domains where the agent used the persona's preferred tool. If the persona prefers Linear for task management but the agent used Jira, this scores 0.0 for that domain. |
| **Tone Appropriateness** | 0.10 | LLM-judged appropriateness of messages sent to sensitive recipients (0.0 = inappropriate, 0.5 = acceptable, 1.0 = exemplary). Defaults to 0.5 when no LLM judge is configured. |
| **Cross-Platform Consistency** | (separate) | Checks entity-notification coherence and reassignment notification completeness across platforms. Reported separately, not included in weighted total. |

**Composite score**: `sum(metric_i * weight_i)` for each task, averaged across k runs.

**Pass^k**: 1.0 if ALL k runs of a task achieve outcome >= 0.5, else 0.0. Measures consistency, not just peak performance.

## Adversarial Tasks

KLIK-Bench includes adversarial tasks designed to test agent robustness:

- **Holiday conflict detection** (`kb-019`): The agent receives a meeting scheduling request, but the persona's session history reveals that the proposed date falls on a team-wide holiday that was decided in a previous meeting. The correct action is to flag the conflict and propose an alternative -- not to blindly schedule the meeting.

- **Ambiguous volunteer resolution** (`kb-020`): A meeting transcript mentions multiple people who "could" handle a task, but only one person explicitly volunteered. The agent must correctly identify the volunteer from session context rather than assigning the task to someone who was merely mentioned.

These tasks specifically test whether agents can reason over temporal context and resolve ambiguity using persona memory, rather than taking the most literal interpretation of the instruction.

## Leaderboard

Results will be published on the [KLIK-Bench HuggingFace Dataset](https://huggingface.co/datasets/ChengyiX/KLIK-Bench).

To submit results, run the benchmark with your agent and upload via:

```bash
python scripts/upload_to_hf.py --token $HF_TOKEN
```

## Citation

If you use KLIK-Bench in your research, please cite:

```bibtex
@misc{klik_bench_2026,
    title={KLIK-Bench: Benchmarking AI Agents on Memory-Grounded Multi-Tool Orchestration},
    author={KLIK Team},
    year={2026},
    url={https://github.com/minervacap2022/KLIK-Bench},
}
```

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
