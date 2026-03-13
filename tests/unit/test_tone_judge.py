"""Tests for ToneJudge — LLM-based tone evaluation for sensitive communications."""

import pytest

from klik_bench.scoring.tone_judge import ToneJudge, ToneResult


class TestJudgeNoClient:
    @pytest.mark.asyncio
    async def test_no_llm_client_returns_default(self) -> None:
        """No LLM client configured -> returns 0.5 with reasoning."""
        judge = ToneJudge(llm_client=None)
        result = await judge.judge(
            message="Your performance has been below expectations.",
            context="Performance review discussion",
            recipient="marcus.wright",
            sensitivity_reason="employee experiencing burnout",
        )
        assert isinstance(result, ToneResult)
        assert result.score == 0.5
        assert result.reasoning == "No LLM judge configured"


class TestJudgeWithMockClient:
    @pytest.mark.asyncio
    async def test_mock_client_returns_parsed_score(self) -> None:
        """Mock LLM returns JSON -> parsed correctly into ToneResult."""

        class MockLLMClient:
            async def complete(self, prompt: str) -> str:
                return '{"score": 0.85, "reasoning": "Tone is empathetic and professional"}'

        judge = ToneJudge(llm_client=MockLLMClient())
        result = await judge.judge(
            message="I understand this has been a challenging period. Let's discuss how we can better support you.",
            context="Performance review",
            recipient="marcus.wright",
            sensitivity_reason="employee experiencing burnout",
        )
        assert isinstance(result, ToneResult)
        assert result.score == 0.85
        assert result.reasoning == "Tone is empathetic and professional"

    @pytest.mark.asyncio
    async def test_mock_client_low_score(self) -> None:
        """Mock LLM returns low score for inappropriate tone."""

        class MockLLMClient:
            async def complete(self, prompt: str) -> str:
                return '{"score": 0.2, "reasoning": "Too blunt and insensitive"}'

        judge = ToneJudge(llm_client=MockLLMClient())
        result = await judge.judge(
            message="Your output is terrible. Do better.",
            context="Performance review",
            recipient="marcus.wright",
            sensitivity_reason="employee experiencing burnout",
        )
        assert result.score == 0.2
        assert result.reasoning == "Too blunt and insensitive"


class TestJudgeActionLog:
    @pytest.mark.asyncio
    async def test_filters_messages_to_sensitive_recipients(self) -> None:
        """Filters action log for messages to sensitive recipients and scores them."""

        class MockLLMClient:
            async def complete(self, prompt: str) -> str:
                if "marcus.wright" in prompt:
                    return '{"score": 0.9, "reasoning": "Appropriate tone"}'
                return '{"score": 1.0, "reasoning": "Fine"}'

        judge = ToneJudge(llm_client=MockLLMClient())

        action_log = [
            {
                "command": ["slack", "send", "--to", "marcus.wright", "--message", "Let's catch up on your workload."],
                "stdout": "Message sent",
                "stderr": "",
            },
            {
                "command": ["slack", "send", "--to", "alice.chen", "--message", "PR looks good!"],
                "stdout": "Message sent",
                "stderr": "",
            },
        ]

        sensitive_recipients = {"marcus.wright": "employee experiencing burnout"}

        score = await judge.judge_action_log(action_log, sensitive_recipients)
        assert score == 0.9

    @pytest.mark.asyncio
    async def test_multiple_sensitive_messages_averaged(self) -> None:
        """Multiple messages to sensitive recipients are averaged."""

        class MockLLMClient:
            async def complete(self, prompt: str) -> str:
                if "first message" in prompt.lower() or "workload" in prompt.lower():
                    return '{"score": 0.8, "reasoning": "Good"}'
                return '{"score": 0.6, "reasoning": "Could be better"}'

        judge = ToneJudge(llm_client=MockLLMClient())

        action_log = [
            {
                "command": ["slack", "send", "--to", "marcus.wright", "--message", "Checking on your workload"],
                "stdout": "Message sent",
                "stderr": "",
            },
            {
                "command": ["email", "send", "--to", "marcus.wright", "--subject", "Follow up", "--body", "Status update needed"],
                "stdout": "Email sent",
                "stderr": "",
            },
        ]

        sensitive_recipients = {"marcus.wright": "employee experiencing burnout"}

        score = await judge.judge_action_log(action_log, sensitive_recipients)
        assert score == pytest.approx(0.7, abs=0.01)


class TestNoSensitiveMessages:
    @pytest.mark.asyncio
    async def test_no_messages_to_sensitive_people(self) -> None:
        """No messages to sensitive recipients -> 1.0 (nothing to judge)."""
        judge = ToneJudge(llm_client=None)

        action_log = [
            {
                "command": ["slack", "send", "--to", "alice.chen", "--message", "PR approved"],
                "stdout": "Message sent",
                "stderr": "",
            },
        ]

        sensitive_recipients = {"marcus.wright": "employee experiencing burnout"}

        score = await judge.judge_action_log(action_log, sensitive_recipients)
        assert score == 1.0

    @pytest.mark.asyncio
    async def test_empty_sensitive_recipients(self) -> None:
        """Empty sensitive recipients dict -> 1.0."""
        judge = ToneJudge(llm_client=None)

        action_log = [
            {
                "command": ["slack", "send", "--to", "anyone", "--message", "Hello"],
                "stdout": "Message sent",
                "stderr": "",
            },
        ]

        score = await judge.judge_action_log(action_log, {})
        assert score == 1.0
