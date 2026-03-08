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

    def test_agent_diary_is_included_in_context(self) -> None:
        """When agent_diary is provided, it appears in context with delimiters."""
        summary = {"user": {"name": "Test"}, "target_date": "2026-06-01"}
        diary = "Dias 27-30 viajei à Irlanda e saí da dieta."
        result = build_agent_context(summary, agent_diary=diary)
        assert diary in result
        assert "Notas do usuário" in result
        assert "Fim das notas" in result

    def test_agent_diary_empty_does_not_add_notes_section(self) -> None:
        """When agent_diary is empty, notes section is not added."""
        result = build_agent_context({}, agent_diary="")
        assert "Notas do usuário" not in result

    def test_agent_diary_none_does_not_add_notes_section(self) -> None:
        """When agent_diary is None, notes section is not added."""
        result = build_agent_context({}, agent_diary=None)
        assert "Notas do usuário" not in result

    def test_agent_diary_truncated_to_2000_chars(self) -> None:
        """Diary text longer than 2000 chars is truncated."""
        diary = "A" * 2500
        result = build_agent_context({}, agent_diary=diary)
        assert "A" * 2000 in result
        assert "A" * 2001 not in result

    def test_prompt_is_non_empty(self) -> None:
        """CHATGPT_PROMPT constant is non-empty."""
        assert len(CHATGPT_PROMPT) > 50
        assert "nutricionista" in CHATGPT_PROMPT


class TestWrapReportDiary:
    """Tests for diary in wrap_report_for_chatgpt context."""

    def test_diary_appended_to_context(self) -> None:
        """wrap_report_for_chatgpt appends diary to agent.context."""
        summary = {"weight": {}, "nutrition": {}}
        result = wrap_report_for_chatgpt(summary, agent_diary="Viajei na semana 3.")
        assert "Viajei na semana 3." in result["agent"]["context"]
        assert "Notas do usuário" in result["agent"]["context"]
        assert "diary" not in result["agent"]

    def test_empty_diary_not_in_context(self) -> None:
        """wrap_report_for_chatgpt does not add notes section when diary is empty."""
        summary = {"weight": {}, "nutrition": {}}
        result = wrap_report_for_chatgpt(summary, agent_diary="")
        assert "Notas do usuário" not in result["agent"]["context"]
        assert "diary" not in result["agent"]

    def test_no_diary_field_in_agent(self) -> None:
        """wrap_report_for_chatgpt never includes a diary key in agent."""
        summary = {"weight": {}, "nutrition": {}}
        result = wrap_report_for_chatgpt(summary)
        assert "diary" not in result["agent"]
