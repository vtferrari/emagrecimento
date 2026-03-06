"""Unit tests for chatgpt_export module."""

import pytest

from emagrecimento.application.presenters.chatgpt_export import (
    CHATGPT_PROMPT,
    build_agent_context,
    wrap_report_for_chatgpt,
)


class TestBuildAgentContext:
    """Tests for build_agent_context."""

    def test_empty_summary_returns_base_context(self) -> None:
        """Empty summary produces minimal context without user details."""
        result = build_agent_context({})
        assert "Relatório de cutting" in result
        assert "MyFitnessPal" in result
        assert "Treino alvo: 4 sessões/semana" in result

    def test_full_user_and_targets_in_context(self) -> None:
        """Summary with user and targets produces complete context."""
        summary = {
            "user": {"name": "Sibele", "age": 30, "height_cm": 154, "weight_kg": 66.3},
            "target_date": "2026-06-04",
            "meta": {
                "adherence_targets": {
                    "calorie_range": [1460, 1612],
                    "protein_g": 119,
                    "fiber_g": 22,
                    "sessions_per_week": 4,
                }
            },
        }
        result = build_agent_context(summary)
        assert "Sibele" in result
        assert "30 anos" in result
        assert "154cm" in result
        assert "66.3kg" in result
        assert "2026-06-04" in result
        assert "1460-1612" in result
        assert "119g" in result
        assert "22g" in result

    def test_partial_user_handled(self) -> None:
        """Partial user data does not break context."""
        summary = {"user": {"name": "Test"}, "target_date": ""}
        result = build_agent_context(summary)
        assert "Test" in result


class TestWrapReportForChatgpt:
    """Tests for wrap_report_for_chatgpt."""

    def test_returns_agent_and_report_structure(self) -> None:
        """Output has agent.prompt, agent.context and report."""
        summary = {"weight": {"latest_weight_kg": 70}, "nutrition": {}}
        result = wrap_report_for_chatgpt(summary)
        assert "agent" in result
        assert "report" in result
        assert "prompt" in result["agent"]
        assert "context" in result["agent"]
        assert result["report"] == summary

    def test_prompt_is_non_empty(self) -> None:
        """CHATGPT_PROMPT constant is non-empty."""
        assert len(CHATGPT_PROMPT) > 50
        assert "nutricionista" in CHATGPT_PROMPT
