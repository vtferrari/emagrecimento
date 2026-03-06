"""Unit tests for domain value objects."""

import math

import pandas as pd
import pytest

from emagrecimento.domain.value_objects import find_column, normalize_text, parse_duration_minutes, parse_number


class TestNormalizeText:
    """Tests for normalize_text."""

    def test_lowercases_and_strips(self) -> None:
        assert normalize_text("  DATA  ") == "data"

    def test_normalizes_unicode(self) -> None:
        assert normalize_text("Proteínas") == "proteinas"

    def test_collapses_whitespace(self) -> None:
        assert normalize_text("Data   da   Medida") == "data da medida"


class TestFindColumn:
    """Tests for find_column."""

    def test_finds_exact_match(self) -> None:
        cols = ["Data", "Peso", "Calorias"]
        assert find_column(cols, ["Data", "Date"]) == "Data"

    def test_finds_partial_match(self) -> None:
        cols = ["Data da Medida", "Peso (kg)"]
        assert find_column(cols, ["Data", "Date"]) == "Data da Medida"

    def test_raises_when_not_found(self) -> None:
        cols = ["X", "Y"]
        with pytest.raises(KeyError, match="Nenhuma coluna encontrada"):
            find_column(cols, ["Data"])

    def test_finds_body_fat_column(self) -> None:
        cols = ["Data", "Body Fat %", "Peso"]
        assert find_column(cols, ["Body Fat %", "Body Fat", "Gordura corporal"]) == "Body Fat %"

    def test_finds_acucar_column(self) -> None:
        cols = ["Data", "Calorias", "Açucar", "Proteínas (g)"]
        assert find_column(cols, ["Açucar", "Açúcar", "Sugar"]) == "Açucar"

    def test_finds_refeicao_column(self) -> None:
        cols = ["Data", "Refeição", "Calorias"]
        assert find_column(cols, ["Refeição", "Meal"]) == "Refeição"


class TestParseNumber:
    """Tests for parse_number."""

    def test_returns_none_for_none(self) -> None:
        assert parse_number(None) is None

    def test_returns_none_for_empty_string(self) -> None:
        assert parse_number("") is None
        assert parse_number("   ") is None

    def test_parses_integer(self) -> None:
        assert parse_number(42) == 42.0
        assert parse_number("42") == 42.0

    def test_parses_float(self) -> None:
        assert parse_number(84.5) == 84.5
        assert parse_number("84.5") == 84.5

    def test_parses_comma_decimal(self) -> None:
        assert parse_number("84,5") == 84.5

    def test_parses_thousands_separator_comma(self) -> None:
        # European: comma as decimal would give 1.85; comma as thousands -> 1,850 -> 1850
        assert parse_number("1,850") == 1850.0

    def test_returns_none_for_nan(self) -> None:
        assert parse_number(float("nan")) is None

    def test_returns_none_for_invalid(self) -> None:
        assert parse_number("abc") is None
        assert parse_number("--") is None


class TestParseDurationMinutes:
    """Tests for parse_duration_minutes."""

    def test_plain_number(self) -> None:
        assert parse_duration_minutes(45) == 45.0
        assert parse_duration_minutes("45") == 45.0

    def test_hh_mm_format(self) -> None:
        assert parse_duration_minutes("1:30") == 90.0
        assert parse_duration_minutes("2:15") == 135.0

    def test_text_duration(self) -> None:
        assert parse_duration_minutes("45 min") == 45.0
        assert parse_duration_minutes("1h 30min") == 90.0
        assert parse_duration_minutes("1h30") == 90.0

    def test_values_over_600_treated_as_seconds(self) -> None:
        result = parse_duration_minutes(26621)  # 26621 sec = 443 min
        assert 443 <= result <= 444
        assert parse_duration_minutes(600) == 600.0  # Exactly 600 stays

    def test_caps_at_600(self) -> None:
        assert parse_duration_minutes("10:00") == 600.0  # 10h = 600 min
        assert parse_duration_minutes(500) == 500.0  # Under 600, kept as-is

    def test_returns_none_for_invalid(self) -> None:
        assert parse_duration_minutes(None) is None
        assert parse_duration_minutes("") is None
        assert parse_duration_minutes("invalid") is None
