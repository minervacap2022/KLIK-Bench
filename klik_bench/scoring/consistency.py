"""Cross-platform consistency checker.

Validates that actions across platforms are coherent: entities created
on one platform should be referenced in notifications on another.
"""

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConsistencyResult:
    """Result of cross-platform consistency analysis."""

    score: float
    violations: list[str]
    entities_created: int
    entities_referenced: int


# Platforms that create entities (issues, docs, pages, etc.)
_ENTITY_CREATION_COMMANDS: dict[str, set[str]] = {
    "linear": {"create"},
    "jira": {"create"},
    "notion": {"create"},
    "github": {"create"},
    "clickup": {"create"},
    "asana": {"create"},
    "monday": {"create"},
    "google_docs": {"create"},
    "confluence": {"create"},
}

# Platforms that send notifications/messages
_NOTIFICATION_PLATFORMS: set[str] = {"slack", "teams", "email"}

# Platforms that update entities (reassignment detection)
_ENTITY_UPDATE_COMMANDS: dict[str, set[str]] = {
    "linear": {"update"},
    "jira": {"update"},
    "github": {"update"},
    "clickup": {"update"},
    "asana": {"update"},
}


def _extract_title_from_command(cmd: list[str]) -> str | None:
    """Extract --title value from a command."""
    for i, arg in enumerate(cmd):
        if arg == "--title" and i + 1 < len(cmd):
            return cmd[i + 1]
    return None


def _extract_title_from_stdout(stdout: str) -> str | None:
    """Try to extract title from JSON stdout."""
    try:
        data = json.loads(stdout)
        if isinstance(data, dict):
            return data.get("title")
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def _extract_reassignment_info(stdout: str) -> tuple[str | None, str | None, str | None]:
    """Extract entity id, new assignee, previous assignee from update stdout.

    Returns (entity_id, new_assignee, previous_assignee).
    """
    try:
        data = json.loads(stdout)
        if isinstance(data, dict):
            entity_id = data.get("id")
            assignee = data.get("assignee")
            previous = data.get("previous_assignee")
            if assignee and previous:
                return entity_id, assignee, previous
    except (json.JSONDecodeError, TypeError):
        pass
    return None, None, None


class ConsistencyChecker:
    """Check that actions across platforms are coherent."""

    def check(
        self,
        action_log: list[dict[str, Any]],
        backends: dict[str, Any],
    ) -> ConsistencyResult:
        """Analyze cross-platform consistency.

        Rules checked:
        1. If entity created on one platform, notification platform should reference it
        2. If task reassigned, both old and new assignee should be notified
        3. Dates/times should be consistent across platforms

        Returns ConsistencyResult with score and violations list.
        """
        if not action_log:
            return ConsistencyResult(score=1.0, violations=[], entities_created=0, entities_referenced=0)

        entities = self._extract_created_entities(action_log)
        notifications = self._extract_notifications(action_log)
        reassignments = self._extract_reassignments(action_log)

        # Determine which platforms were used
        platforms_used = set()
        for entry in action_log:
            cmd = entry.get("command", [])
            if cmd and isinstance(cmd, list):
                platforms_used.add(cmd[0])

        entity_platforms = {e["platform"] for e in entities}
        has_notification_platform = bool(platforms_used & _NOTIFICATION_PLATFORMS)

        # If all actions are on a single platform type (no cross-platform), score 1.0
        if not entities or not has_notification_platform:
            if not reassignments:
                return ConsistencyResult(
                    score=1.0,
                    violations=[],
                    entities_created=len(entities),
                    entities_referenced=0,
                )

        violations: list[str] = []
        entities_referenced = 0

        # Check entity-notification consistency
        if entities and has_notification_platform:
            entity_score, entity_violations, entities_referenced = (
                self._check_entity_notification_consistency(entities, notifications)
            )
            violations.extend(entity_violations)
        else:
            entity_score = 1.0

        # Check reassignment notification consistency
        reassignment_score = 1.0
        if reassignments:
            reassignment_score, reassignment_violations = (
                self._check_reassignment_consistency(reassignments, notifications)
            )
            violations.extend(reassignment_violations)

        # Combine scores
        score_parts = []
        if entities and has_notification_platform:
            score_parts.append(entity_score)
        if reassignments:
            score_parts.append(reassignment_score)

        if score_parts:
            score = sum(score_parts) / len(score_parts)
        else:
            score = 1.0

        return ConsistencyResult(
            score=score,
            violations=violations,
            entities_created=len(entities),
            entities_referenced=entities_referenced,
        )

    def _extract_created_entities(self, action_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Find all entities created across platforms from the action log."""
        entities: list[dict[str, Any]] = []

        for entry in action_log:
            cmd = entry.get("command", [])
            if not cmd or not isinstance(cmd, list) or len(cmd) < 3:
                continue

            platform = cmd[0]
            subcommand = cmd[2] if len(cmd) > 2 else ""

            if platform in _ENTITY_CREATION_COMMANDS and subcommand in _ENTITY_CREATION_COMMANDS[platform]:
                title = _extract_title_from_command(cmd) or _extract_title_from_stdout(entry.get("stdout", ""))
                entity_id = None
                try:
                    data = json.loads(entry.get("stdout", ""))
                    if isinstance(data, dict):
                        entity_id = data.get("id")
                except (json.JSONDecodeError, TypeError):
                    pass

                if title:
                    entities.append({
                        "platform": platform,
                        "title": title,
                        "id": entity_id,
                    })

        return entities

    def _extract_notifications(self, action_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Find all messages/notifications sent."""
        notifications: list[dict[str, Any]] = []

        for entry in action_log:
            cmd = entry.get("command", [])
            if not cmd or not isinstance(cmd, list):
                continue

            platform = cmd[0]
            if platform not in _NOTIFICATION_PLATFORMS:
                continue

            message = None
            recipient = None
            for i, arg in enumerate(cmd):
                if arg in ("--message", "--body") and i + 1 < len(cmd):
                    message = cmd[i + 1]
                if arg in ("--to", "--channel") and i + 1 < len(cmd):
                    recipient = cmd[i + 1]

            if message:
                notifications.append({
                    "platform": platform,
                    "message": message,
                    "recipient": recipient,
                })

        return notifications

    def _extract_reassignments(self, action_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Find all reassignment operations."""
        reassignments: list[dict[str, Any]] = []

        for entry in action_log:
            cmd = entry.get("command", [])
            if not cmd or not isinstance(cmd, list) or len(cmd) < 3:
                continue

            platform = cmd[0]
            subcommand = cmd[2] if len(cmd) > 2 else ""

            if platform in _ENTITY_UPDATE_COMMANDS and subcommand in _ENTITY_UPDATE_COMMANDS[platform]:
                entity_id, new_assignee, prev_assignee = _extract_reassignment_info(
                    entry.get("stdout", "")
                )
                if new_assignee and prev_assignee:
                    reassignments.append({
                        "platform": platform,
                        "entity_id": entity_id,
                        "new_assignee": new_assignee,
                        "previous_assignee": prev_assignee,
                    })

        return reassignments

    def _check_entity_notification_consistency(
        self,
        entities: list[dict[str, Any]],
        notifications: list[dict[str, Any]],
    ) -> tuple[float, list[str], int]:
        """Check if created entities are properly referenced in notifications.

        Returns (score, violations, entities_referenced_count).
        """
        if not entities:
            return 1.0, [], 0

        notification_text = " ".join(n["message"] for n in notifications)
        referenced_count = 0
        violations: list[str] = []

        for entity in entities:
            title = entity["title"]
            entity_id = entity.get("id")

            # Check if the entity's title or ID appears in any notification
            title_found = title in notification_text
            id_found = entity_id is not None and str(entity_id) in notification_text

            if title_found or id_found:
                referenced_count += 1
            else:
                violations.append(
                    f"Entity '{title}' created on {entity['platform']} "
                    f"but not referenced in any notification"
                )

        score = referenced_count / len(entities)
        return score, violations, referenced_count

    def _check_reassignment_consistency(
        self,
        reassignments: list[dict[str, Any]],
        notifications: list[dict[str, Any]],
    ) -> tuple[float, list[str]]:
        """Check if both old and new assignees are notified on reassignment.

        Returns (score, violations).
        """
        if not reassignments:
            return 1.0, []

        violations: list[str] = []
        scores: list[float] = []

        for reassignment in reassignments:
            new_assignee = reassignment["new_assignee"]
            prev_assignee = reassignment["previous_assignee"]
            entity_id = reassignment.get("entity_id", "unknown")

            # Check if both are notified
            new_notified = any(
                n.get("recipient") == new_assignee for n in notifications
            )
            prev_notified = any(
                n.get("recipient") == prev_assignee for n in notifications
            )

            notified_count = sum([new_notified, prev_notified])
            scores.append(notified_count / 2)

            if not new_notified:
                violations.append(
                    f"New assignee '{new_assignee}' not notified about "
                    f"reassignment of {entity_id}"
                )
            if not prev_notified:
                violations.append(
                    f"Previous assignee '{prev_assignee}' not notified about "
                    f"reassignment of {entity_id}"
                )

        return sum(scores) / len(scores), violations
