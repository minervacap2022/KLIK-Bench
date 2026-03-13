"""Tests for KlikScorer — memory utilization + preference adherence scoring."""

import pytest

from klik_bench.scoring.scorer import KlikScorer


class TestMemoryUtilizationAllUsed:
    def test_all_required_memory_found(self) -> None:
        """All required memory fields appear in action log -> 1.0."""
        scorer = KlikScorer()

        persona_context = {
            "entity_graph": {
                "people": [
                    {"name": "Alice Chen", "role": "engineer"},
                    {"name": "Bob Park", "role": "designer"},
                ],
            },
            "session_history": {
                "sess_001": {"summary": "Sprint planning discussion"},
            },
            "preferences": {
                "communication": "slack",
            },
        }

        # Action log that references all required memory fields
        action_log = [
            {
                "command": ["slack", "send", "--channel", "#team", "--message", "Alice Chen and Bob Park assigned"],
                "stdout": "Message sent",
                "stderr": "",
            },
            {
                "command": ["slack", "send", "--channel", "#team", "--message", "Continuing from Sprint planning discussion"],
                "stdout": "Message sent",
                "stderr": "",
            },
        ]

        memory_required = [
            "entity_graph.people",
            "session_history.sess_001",
            "preferences.communication",
        ]

        score = scorer.score_memory_utilization(action_log, memory_required, persona_context)
        assert score == 1.0


class TestMemoryUtilizationNoneUsed:
    def test_no_memory_referenced(self) -> None:
        """No required memory referenced in action log -> 0.0."""
        scorer = KlikScorer()

        persona_context = {
            "entity_graph": {
                "people": [
                    {"name": "Alice Chen", "role": "engineer"},
                ],
            },
            "preferences": {
                "communication": "slack",
            },
        }

        # Action log that references none of the required memory
        action_log = [
            {
                "command": ["linear", "issue", "create", "--title", "Fix bug"],
                "stdout": "Issue LIN-42 created",
                "stderr": "",
            },
        ]

        memory_required = [
            "entity_graph.people",
            "preferences.communication",
        ]

        score = scorer.score_memory_utilization(action_log, memory_required, persona_context)
        assert score == 0.0


class TestMemoryUtilizationPartial:
    def test_half_memory_used(self) -> None:
        """Half of required memory fields used -> 0.5."""
        scorer = KlikScorer()

        persona_context = {
            "entity_graph": {
                "people": [
                    {"name": "Alice Chen", "role": "engineer"},
                ],
            },
            "preferences": {
                "communication": "slack",
            },
        }

        # Only references people, not communication preference
        action_log = [
            {
                "command": ["linear", "issue", "create", "--title", "Alice Chen review needed"],
                "stdout": "Issue created",
                "stderr": "",
            },
        ]

        memory_required = [
            "entity_graph.people",
            "preferences.communication",
        ]

        score = scorer.score_memory_utilization(action_log, memory_required, persona_context)
        assert score == 0.5

    def test_empty_memory_required(self) -> None:
        """No required memory -> 1.0 (nothing to check)."""
        scorer = KlikScorer()
        score = scorer.score_memory_utilization(
            action_log=[{"command": ["gh", "issue", "create"], "stdout": "", "stderr": ""}],
            memory_required=[],
            persona_context={},
        )
        assert score == 1.0


class TestPreferenceAdherenceCorrect:
    def test_used_preferred_tool(self) -> None:
        """Agent used the preferred task management tool -> 1.0."""
        scorer = KlikScorer()

        action_log = [
            {
                "command": ["linear", "issue", "create", "--title", "New task"],
                "stdout": "Issue LIN-42 created",
                "stderr": "",
            },
        ]

        persona_preferences = {
            "task_management": "linear",
            "documentation": "notion",
            "communication": "slack",
            "file_storage": "google_drive",
        }

        score = scorer.score_preference_adherence(action_log, persona_preferences)
        assert score == 1.0


class TestPreferenceAdherenceWrong:
    def test_used_wrong_tool(self) -> None:
        """Agent used jira but preferred linear -> 0.0."""
        scorer = KlikScorer()

        action_log = [
            {
                "command": ["jira", "issue", "create", "--project", "PROJ", "--summary", "New task"],
                "stdout": "Issue PROJ-1 created",
                "stderr": "",
            },
        ]

        persona_preferences = {
            "task_management": "linear",
            "documentation": "notion",
            "communication": "slack",
            "file_storage": "google_drive",
        }

        score = scorer.score_preference_adherence(action_log, persona_preferences)
        assert score == 0.0


class TestPreferenceAdherenceMixed:
    def test_some_correct_some_wrong(self) -> None:
        """Agent used correct task mgmt tool but wrong comm tool -> 0.5."""
        scorer = KlikScorer()

        action_log = [
            {
                "command": ["linear", "issue", "create", "--title", "New task"],
                "stdout": "Issue LIN-42 created",
                "stderr": "",
            },
            {
                "command": ["teams", "send", "--channel", "#general", "--message", "Hello"],
                "stdout": "Message sent",
                "stderr": "",
            },
        ]

        persona_preferences = {
            "task_management": "linear",
            "documentation": "notion",
            "communication": "slack",
            "file_storage": "google_drive",
        }

        score = scorer.score_preference_adherence(action_log, persona_preferences)
        assert score == 0.5


class TestPreferenceAdherenceNoToolUsage:
    def test_agent_used_no_recognized_tools(self) -> None:
        """Agent used no domain tools -> 0.0 (no domains matched)."""
        scorer = KlikScorer()

        action_log = [
            {
                "command": ["echo", "hello"],
                "stdout": "hello",
                "stderr": "",
            },
        ]

        persona_preferences = {
            "task_management": "linear",
            "documentation": "notion",
            "communication": "slack",
            "file_storage": "google_drive",
        }

        score = scorer.score_preference_adherence(action_log, persona_preferences)
        assert score == 0.0
