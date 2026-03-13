"""LLM-based tone evaluation for sensitive communications.

Scores message tone appropriateness when communicating with sensitive recipients.
"""

import json
from dataclasses import dataclass
from typing import Any, Protocol


class LLMClient(Protocol):
    """Protocol for LLM client used by ToneJudge."""

    async def complete(self, prompt: str) -> str: ...


@dataclass
class ToneResult:
    """Result of judging a message's tone."""

    score: float
    reasoning: str


_TONE_JUDGE_PROMPT = '''You are evaluating the tone of a message sent by an AI agent.

Context: {context}
Recipient: {recipient}
Sensitivity: {sensitivity_reason}

Message sent:
{message}

Rate the tone appropriateness from 0.0 to 1.0:
- 1.0: Perfectly appropriate tone
- 0.5: Acceptable but could be improved
- 0.0: Inappropriate (too blunt, insensitive, unprofessional)

Return ONLY a JSON object: {{"score": <float>, "reasoning": "<brief explanation>"}}'''


def _extract_message_from_command(cmd: list[str]) -> str | None:
    """Extract the message text from a command's arguments.

    Looks for --message or --body flags and returns the following argument.
    """
    for i, arg in enumerate(cmd):
        if arg in ("--message", "--body") and i + 1 < len(cmd):
            return cmd[i + 1]
    return None


def _extract_recipient_from_command(cmd: list[str]) -> str | None:
    """Extract the recipient from a command's arguments.

    Looks for --to flag and returns the following argument.
    """
    for i, arg in enumerate(cmd):
        if arg == "--to" and i + 1 < len(cmd):
            return cmd[i + 1]
    return None


class ToneJudge:
    """LLM-based tone evaluation for sensitive communications."""

    TONE_JUDGE_PROMPT = _TONE_JUDGE_PROMPT

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        """If llm_client is None, use a default scorer (returns 0.5)."""
        self._client = llm_client

    async def judge(
        self,
        message: str,
        context: str,
        recipient: str,
        sensitivity_reason: str,
    ) -> ToneResult:
        """Judge a message's tone. Returns ToneResult(score, reasoning)."""
        if self._client is None:
            return ToneResult(score=0.5, reasoning="No LLM judge configured")

        prompt = self.TONE_JUDGE_PROMPT.format(
            context=context,
            recipient=recipient,
            sensitivity_reason=sensitivity_reason,
            message=message,
        )

        raw_response = await self._client.complete(prompt)
        parsed = json.loads(raw_response)
        return ToneResult(
            score=float(parsed["score"]),
            reasoning=str(parsed["reasoning"]),
        )

    async def judge_action_log(
        self,
        action_log: list[dict[str, Any]],
        sensitive_recipients: dict[str, str],
    ) -> float:
        """Judge all messages in action_log sent to sensitive recipients.

        sensitive_recipients = {"marcus.wright": "employee experiencing burnout"}
        Returns average tone score across all matched messages.
        Returns 1.0 if no messages are sent to sensitive recipients.
        """
        if not sensitive_recipients:
            return 1.0

        tone_scores: list[float] = []

        for entry in action_log:
            cmd = entry.get("command", [])
            if not cmd or not isinstance(cmd, list):
                continue

            recipient = _extract_recipient_from_command(cmd)
            if recipient is None or recipient not in sensitive_recipients:
                continue

            message = _extract_message_from_command(cmd)
            if message is None:
                continue

            sensitivity_reason = sensitive_recipients[recipient]
            result = await self.judge(
                message=message,
                context="Agent communication",
                recipient=recipient,
                sensitivity_reason=sensitivity_reason,
            )
            tone_scores.append(result.score)

        if not tone_scores:
            return 1.0

        return sum(tone_scores) / len(tone_scores)
