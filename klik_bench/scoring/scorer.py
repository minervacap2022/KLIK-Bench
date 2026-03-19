"""KLIK-Bench specific scoring — memory utilization + preference adherence.

Scores how well an agent leverages persona memory and respects tool preferences.
"""

from typing import Any


# Maps preference categories to known tool binary names
# Aligned with KK_exec tools.yaml sub_categories
_TOOL_DOMAIN_MAP: dict[str, list[str]] = {
    "task_management": ["linear", "jira", "clickup", "asana", "monday", "atlassian"],
    "documentation": ["notion", "google_docs", "confluence", "google"],
    "communication": ["slack", "teams", "email", "microsoft"],
    "file_storage": ["google_drive", "onedrive", "dropbox", "google", "microsoft"],
    "calendar": ["google_calendar", "google", "microsoft"],
    "email": ["gmail", "outlook", "google", "microsoft"],
    "code": ["github", "gh"],
    "web_search": ["web_search", "jina", "duckduckgo"],
}


def _resolve_path(context: dict[str, Any], path: str) -> Any:
    """Resolve a dot-separated path in a nested dict.

    Example: "entity_graph.people" resolves to context["entity_graph"]["people"].
    Returns None if path cannot be resolved.
    """
    current = context
    for key in path.split("."):
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def _stringify_values(value: Any) -> list[str]:
    """Extract all string representations from a value for matching.

    Recursively walks dicts and lists to extract string values.
    """
    strings: list[str] = []

    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, dict):
        for v in value.values():
            strings.extend(_stringify_values(v))
    elif isinstance(value, list):
        for item in value:
            strings.extend(_stringify_values(item))
    else:
        strings.append(str(value))

    return strings


def _action_log_text(action_log: list[dict[str, Any]]) -> str:
    """Concatenate all command args and stdout from an action log into searchable text."""
    parts: list[str] = []
    for entry in action_log:
        cmd = entry.get("command", [])
        if isinstance(cmd, list):
            parts.extend(str(c) for c in cmd)
        stdout = entry.get("stdout", "")
        if stdout:
            parts.append(str(stdout))
    return " ".join(parts)


def _tool_to_domain(tool_name: str) -> str | None:
    """Map a tool binary name to its preference domain."""
    for domain, tools in _TOOL_DOMAIN_MAP.items():
        if tool_name in tools:
            return domain
    return None


class KlikScorer:
    """KLIK-Bench specific scoring -- memory utilization + preference adherence."""

    def score_memory_utilization(
        self,
        action_log: list[dict[str, Any]],
        memory_required: list[str],
        persona_context: dict[str, Any],
    ) -> float:
        """Score how well the agent used required memory fields.

        For each required path:
          1. Resolve the path in persona_context to get expected values
          2. Extract string representations of those values
          3. Check if any of those strings appear in action_log command args or stdout
          4. Score = fraction of required memory fields actually used

        Returns 0.0-1.0.
        """
        if not memory_required:
            return 1.0

        log_text = _action_log_text(action_log)
        used_count = 0

        for path in memory_required:
            resolved = _resolve_path(persona_context, path)
            if resolved is None:
                continue

            value_strings = _stringify_values(resolved)
            if any(vs in log_text for vs in value_strings if vs):
                used_count += 1

        return used_count / len(memory_required)

    def score_preference_adherence(
        self,
        action_log: list[dict[str, Any]],
        persona_preferences: dict[str, str],
    ) -> float:
        """Score whether agent used the user's preferred tools.

        For each command in the action log, determine the domain (if any).
        For each domain where agent used a tool, check if it matches the preference.

        Returns 0.0-1.0 (fraction of correct tool choices).
        Returns 0.0 if agent used no recognized domain tools.
        """
        domain_correct: dict[str, bool] = {}

        for entry in action_log:
            cmd = entry.get("command", [])
            if not cmd or not isinstance(cmd, list):
                continue

            tool_name = cmd[0]
            domain = _tool_to_domain(tool_name)
            if domain is None:
                continue

            preferred = persona_preferences.get(domain)
            if preferred is None:
                continue

            # If domain already seen, keep existing result (first tool usage per domain)
            if domain not in domain_correct:
                domain_correct[domain] = (tool_name == preferred)

        if not domain_correct:
            return 0.0

        correct_count = sum(1 for v in domain_correct.values() if v)
        return correct_count / len(domain_correct)
