"""Unit tests for Withings PDF metrics parser."""

import pytest

from emagrecimento.infrastructure.pdf_metrics_parser import WithingsPdfMetricsParser


class TestWithingsPdfMetricsParser:
    """Tests for WithingsPdfMetricsParser."""

    def setup_method(self) -> None:
        self.parser = WithingsPdfMetricsParser()

    def test_parses_weight(self) -> None:
        text = "Weight 84.5 kg Latest -0.3 kg Trend"
        result = self.parser.parse(text)
        assert result["latest_weight_kg"] == 84.5
        assert result["weight_trend_kg"] == -0.3

    def test_parses_bmr(self) -> None:
        text = "BMR 1,850 kcal Latest"  # Comma as thousands (European)
        result = self.parser.parse(text)
        assert result["bmr_kcal"] == 1850.0

    def test_parses_daily_steps(self) -> None:
        text = "Daily Steps 8,500 steps Average"  # Comma as thousands
        result = self.parser.parse(text)
        assert result["daily_steps_avg"] == 8500.0

    def test_parses_sleep_efficiency(self) -> None:
        text = "Sleep Efficiency 85 % Average"
        result = self.parser.parse(text)
        assert result["sleep_efficiency_pct"] == 85.0

    def test_returns_none_for_missing_metrics(self) -> None:
        result = self.parser.parse("Some unrelated text")
        assert result["latest_weight_kg"] is None
        assert result["daily_steps_avg"] is None

    def test_parses_full_sample(self, sample_pdf_text: str) -> None:
        result = self.parser.parse(sample_pdf_text)
        assert result["latest_weight_kg"] == 84.5
        assert result["weight_trend_kg"] == -0.3
        assert result["bmr_kcal"] == 1850.0
        assert result["fat_mass_kg"] == 15.2
        assert result["fat_mass_trend_kg"] == -0.5
        assert result["muscle_mass_kg"] == 38.5
        assert result["daily_steps_avg"] == 8500.0
        assert result["sleep_avg"] == "7h30"
        assert result["sleep_efficiency_pct"] == 85.0

    def test_sleep_avg_not_confused_with_active_minutes(self) -> None:
        """Sleep avg must be from Sleep section (7h13), not Daily Active Minutes (1h10)."""
        text = (
            "Daily Active Minutes 1h10 Average "
            "Sleep Duration Average 7h13 Weekdays 7h00 "
            "92 % Efficiency 37 nights"
        )
        result = self.parser.parse(text)
        assert result["sleep_avg"] == "7h13"
        assert result["sleep_efficiency_pct"] == 92.0
        # "1h10" must be parsed as 70 minutes, not 1
        assert result["daily_active_minutes_avg"] == 70

    def test_parser_extracts_water_mass_visceral(self) -> None:
        """Parser extracts water_mass_kg, bone_mass_kg, visceral_fat from medical report text."""
        text = (
            "Weight 90.5 kg Latest Fat Mass 19.8 kg Lean Mass 69.1 kg "
            "Water Mass 48.3 kg Bone Mass 3.4 kg Visceral Fat 3.2 "
            "Muscle Mass 65.7 kg"
        )
        result = self.parser.parse(text)
        assert result["water_mass_kg"] == 48.3
        assert result["bone_mass_kg"] == 3.4
        assert result["visceral_fat"] == 3.2

    def test_parser_extracts_age_and_sex(self) -> None:
        """Parser extracts age_years and biological_sex for form pre-fill."""
        text = "Sibele Schuantes 30yo Weight 66.3 kg Latest BMI 27.9 Cycle Diary Biological Sex: Female."
        result = self.parser.parse(text)
        assert result["age_years"] == 30
        assert result["biological_sex"] == "F"
