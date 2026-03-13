"""Tests for ConsistencyChecker — cross-platform action consistency."""

import pytest

from klik_bench.scoring.consistency import ConsistencyChecker, ConsistencyResult


class TestConsistentActions:
    def test_linear_issue_with_slack_notification(self) -> None:
        """Linear issue created + Slack message referencing it -> 1.0."""
        checker = ConsistencyChecker()

        action_log = [
            {
                "command": ["linear", "issue", "create", "--title", "Fix login bug", "--team", "ENG"],
                "stdout": '{"id": "LIN-42", "title": "Fix login bug"}',
                "stderr": "",
            },
            {
                "command": ["slack", "send", "--channel", "#engineering", "--message", "Created Fix login bug (LIN-42) for the team"],
                "stdout": "Message sent",
                "stderr": "",
            },
        ]

        result = checker.check(action_log, backends={})
        assert isinstance(result, ConsistencyResult)
        assert result.score == 1.0
        assert result.violations == []
        assert result.entities_created >= 1
        assert result.entities_referenced >= 1

    def test_notion_doc_with_slack_notification(self) -> None:
        """Notion doc created + Slack message referencing it -> 1.0."""
        checker = ConsistencyChecker()

        action_log = [
            {
                "command": ["notion", "page", "create", "--title", "Q1 Planning", "--parent", "Engineering"],
                "stdout": '{"id": "page-abc", "title": "Q1 Planning"}',
                "stderr": "",
            },
            {
                "command": ["slack", "send", "--channel", "#team", "--message", "Created Q1 Planning doc in Notion"],
                "stdout": "Message sent",
                "stderr": "",
            },
        ]

        result = checker.check(action_log, backends={})
        assert result.score == 1.0
        assert result.violations == []


class TestInconsistentActions:
    def test_entity_created_but_no_notification(self) -> None:
        """Linear issue created but Slack message doesn't reference it -> score < 1.0."""
        checker = ConsistencyChecker()

        action_log = [
            {
                "command": ["linear", "issue", "create", "--title", "Fix login bug", "--team", "ENG"],
                "stdout": '{"id": "LIN-42", "title": "Fix login bug"}',
                "stderr": "",
            },
            {
                "command": ["slack", "send", "--channel", "#general", "--message", "Good morning team!"],
                "stdout": "Message sent",
                "stderr": "",
            },
        ]

        result = checker.check(action_log, backends={})
        assert result.score < 1.0
        assert len(result.violations) > 0
        assert result.entities_created >= 1
        assert result.entities_referenced == 0

    def test_reassignment_without_notifying_both(self) -> None:
        """Task reassigned but only one person notified -> violation."""
        checker = ConsistencyChecker()

        action_log = [
            {
                "command": ["linear", "issue", "update", "--id", "LIN-42", "--assignee", "bob.park"],
                "stdout": '{"id": "LIN-42", "assignee": "bob.park", "previous_assignee": "alice.chen"}',
                "stderr": "",
            },
            {
                "command": ["slack", "send", "--to", "bob.park", "--message", "LIN-42 assigned to you"],
                "stdout": "Message sent",
                "stderr": "",
            },
            # Missing: notification to alice.chen about reassignment
        ]

        result = checker.check(action_log, backends={})
        assert result.score < 1.0
        assert len(result.violations) > 0


class TestNoCrossPlatformActions:
    def test_single_platform_only(self) -> None:
        """Single platform only -> 1.0 (nothing cross-platform to check)."""
        checker = ConsistencyChecker()

        action_log = [
            {
                "command": ["linear", "issue", "create", "--title", "Task A"],
                "stdout": '{"id": "LIN-1", "title": "Task A"}',
                "stderr": "",
            },
            {
                "command": ["linear", "issue", "create", "--title", "Task B"],
                "stdout": '{"id": "LIN-2", "title": "Task B"}',
                "stderr": "",
            },
        ]

        result = checker.check(action_log, backends={})
        assert result.score == 1.0
        assert result.violations == []

    def test_empty_action_log(self) -> None:
        """Empty action log -> 1.0 (nothing to check)."""
        checker = ConsistencyChecker()

        result = checker.check([], backends={})
        assert result.score == 1.0
        assert result.violations == []


class TestMultipleEntities:
    def test_some_entities_referenced_some_not(self) -> None:
        """Multiple entities created, some referenced in notifications, some not -> partial score."""
        checker = ConsistencyChecker()

        action_log = [
            {
                "command": ["linear", "issue", "create", "--title", "Fix login bug"],
                "stdout": '{"id": "LIN-42", "title": "Fix login bug"}',
                "stderr": "",
            },
            {
                "command": ["linear", "issue", "create", "--title", "Update docs"],
                "stdout": '{"id": "LIN-43", "title": "Update docs"}',
                "stderr": "",
            },
            {
                "command": ["slack", "send", "--channel", "#eng", "--message", "Created Fix login bug issue"],
                "stdout": "Message sent",
                "stderr": "",
            },
            # Missing: notification about "Update docs"
        ]

        result = checker.check(action_log, backends={})
        assert 0.0 < result.score < 1.0
        assert result.entities_created == 2
        assert result.entities_referenced == 1
        assert len(result.violations) > 0
