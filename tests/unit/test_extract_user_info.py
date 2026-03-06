"""Unit tests for ExtractUserInfoFromFiles use case."""

import math

import pandas as pd

from emagrecimento.application.use_cases.extract_user_info import (
    ExtractUserInfoFromFiles,
)
from emagrecimento.domain.entities import ZipData


class TestExtractUserInfoFromFiles:
    """Tests for ExtractUserInfoFromFiles use case."""

    def test_extracts_weight_from_pdf_when_available(self) -> None:
        """Weight from PDF latest_weight_kg takes precedence."""
        zip_data = ZipData(
            measures=pd.DataFrame({"date": [pd.Timestamp("2026-02-01")], "weight": [85.0]}),
            nutrition_daily=pd.DataFrame(),
            exercise_daily=pd.DataFrame(),
        )
        pdf_metrics = {"latest_weight_kg": 84.5}
        use_case = ExtractUserInfoFromFiles()
        result = use_case.execute(zip_data, pdf_metrics)
        assert result["weight_kg"] == 84.5

    def test_extracts_weight_from_measures_when_pdf_missing(self) -> None:
        """Weight from measures last row when PDF has no latest_weight_kg."""
        zip_data = ZipData(
            measures=pd.DataFrame({
                "date": [pd.Timestamp("2026-02-01"), pd.Timestamp("2026-02-02")],
                "weight": [85.0, 84.5],
            }),
            nutrition_daily=pd.DataFrame(),
            exercise_daily=pd.DataFrame(),
        )
        pdf_metrics = {}
        use_case = ExtractUserInfoFromFiles()
        result = use_case.execute(zip_data, pdf_metrics)
        assert result["weight_kg"] == 84.5

    def test_derives_height_from_bmi_and_weight(self) -> None:
        """Height = 100 * sqrt(weight/bmi) when both available."""
        zip_data = ZipData(
            measures=pd.DataFrame(),
            nutrition_daily=pd.DataFrame(),
            exercise_daily=pd.DataFrame(),
        )
        pdf_metrics = {"latest_weight_kg": 80.0, "bmi_avg": 25.0}
        use_case = ExtractUserInfoFromFiles()
        result = use_case.execute(zip_data, pdf_metrics)
        expected_height = int(round(100 * math.sqrt(80 / 25)))
        assert result["height_cm"] == expected_height
        assert 170 <= result["height_cm"] <= 180

    def test_height_clamped_to_valid_range(self) -> None:
        """Height outside 100-250 cm is not included."""
        zip_data = ZipData(
            measures=pd.DataFrame(),
            nutrition_daily=pd.DataFrame(),
            exercise_daily=pd.DataFrame(),
        )
        # weight=100, bmi=10 -> height = 100*sqrt(10) ~ 316 cm, outside valid range
        pdf_metrics = {"latest_weight_kg": 100.0, "bmi_avg": 10.0}
        use_case = ExtractUserInfoFromFiles()
        result = use_case.execute(zip_data, pdf_metrics)
        assert "height_cm" not in result

    def test_extracts_age_and_sex_from_pdf(self) -> None:
        """Age and sex come from PDF metrics."""
        zip_data = ZipData(
            measures=pd.DataFrame(),
            nutrition_daily=pd.DataFrame(),
            exercise_daily=pd.DataFrame(),
        )
        pdf_metrics = {
            "latest_weight_kg": 80.0,
            "age_years": 30,
            "biological_sex": "Male",
        }
        use_case = ExtractUserInfoFromFiles()
        result = use_case.execute(zip_data, pdf_metrics)
        assert result["age"] == 30
        assert result["sex"] == "Male"

    def test_empty_zip_data_returns_only_pdf_fields(self) -> None:
        """When ZipData has empty measures, only PDF metrics are used."""
        zip_data = ZipData(
            measures=pd.DataFrame(),
            nutrition_daily=pd.DataFrame(),
            exercise_daily=pd.DataFrame(),
        )
        pdf_metrics = {"latest_weight_kg": 75.0, "age_years": 25}
        use_case = ExtractUserInfoFromFiles()
        result = use_case.execute(zip_data, pdf_metrics)
        assert result["weight_kg"] == 75.0
        assert result["age"] == 25
        assert "height_cm" not in result

    def test_none_pdf_metrics_uses_only_zip(self) -> None:
        """When pdf_metrics is None, only ZipData is used."""
        zip_data = ZipData(
            measures=pd.DataFrame({
                "date": [pd.Timestamp("2026-02-01")],
                "weight": [82.0],
            }),
            nutrition_daily=pd.DataFrame(),
            exercise_daily=pd.DataFrame(),
        )
        use_case = ExtractUserInfoFromFiles()
        result = use_case.execute(zip_data, None)
        assert result["weight_kg"] == 82.0

    def test_skips_nan_weight_in_measures(self) -> None:
        """NaN weight in measures is skipped."""
        zip_data = ZipData(
            measures=pd.DataFrame({
                "date": [pd.Timestamp("2026-02-01")],
                "weight": [float("nan")],
            }),
            nutrition_daily=pd.DataFrame(),
            exercise_daily=pd.DataFrame(),
        )
        pdf_metrics = {"latest_weight_kg": 70.0}
        use_case = ExtractUserInfoFromFiles()
        result = use_case.execute(zip_data, pdf_metrics)
        assert result["weight_kg"] == 70.0


