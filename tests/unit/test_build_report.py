"""Unit tests for BuildReportUseCase."""

import pytest

from emagrecimento.application.transformers.pdf_report_v2 import build_pdf_report_v2
from emagrecimento.application.use_cases.build_report import BuildReportUseCase
from emagrecimento.domain.entities import ZipData


class TestBuildReportUseCase:
    """Tests for BuildReportUseCase."""

    def setup_method(self) -> None:
        self.use_case = BuildReportUseCase()

    def test_returns_valid_structure(self, sample_zip_data: ZipData) -> None:
        pdf_metrics = {"latest_weight_kg": 84.5, "daily_steps_avg": 8000}
        result = self.use_case.execute(sample_zip_data, pdf_metrics)

        assert "weight" in result
        assert "nutrition" in result
        assert "exercise" in result
        assert "pdf_report" in result

    def test_weight_section_has_required_keys(self, sample_zip_data: ZipData) -> None:
        result = self.use_case.execute(sample_zip_data, {})

        assert "latest_weight_kg" in result["weight"]
        assert "latest_ma5_kg" in result["weight"]
        assert "latest_ma7_kg" in result["weight"]
        assert "weight_history" in result["weight"]
        assert "last_15_days" in result["weight"]

    def test_no_nan_in_output(self, sample_zip_data: ZipData) -> None:
        """Ensure output is JSON-serializable (no NaN)."""
        import json

        result = self.use_case.execute(sample_zip_data, {})
        # Should not raise
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        assert parsed == result

    def test_nutrition_summary_computed(self, sample_zip_data: ZipData) -> None:
        result = self.use_case.execute(sample_zip_data, {})

        assert result["nutrition"]["days_logged"] == 2
        assert result["nutrition"]["avg_calories"] == 1875.0
        assert result["nutrition"]["avg_protein_g"] == 177.5

    def test_exercise_summary_computed(self, sample_zip_data: ZipData) -> None:
        result = self.use_case.execute(sample_zip_data, {})

        assert result["exercise"]["days_logged"] == 2
        assert "avg_exercise_minutes" in result["exercise"]
        assert "avg_steps" in result["exercise"]

    def test_weight_has_total_loss_and_rate(self, sample_zip_data: ZipData) -> None:
        """Weight section includes total_loss_kg, loss_rate_kg_per_week, first_weight_kg."""
        result = self.use_case.execute(sample_zip_data, {})

        assert "total_loss_kg" in result["weight"]
        assert "loss_rate_kg_per_week" in result["weight"]
        assert "first_weight_kg" in result["weight"]
        assert "latest_weight_kg" in result["weight"]
        # sample_measures: first 85.0, last 83.3 -> total_loss = -1.7, ~8 days -> ~-0.15 kg/week
        assert result["weight"]["first_weight_kg"] == 85.0
        assert result["weight"]["latest_weight_kg"] == 83.3
        assert result["weight"]["total_loss_kg"] == pytest.approx(-1.7, abs=0.01)

    def test_nutrition_has_carbs_fat_and_history(self, sample_zip_data: ZipData) -> None:
        """Nutrition includes avg_carbs_g, avg_fat_g, and nutrition_history."""
        result = self.use_case.execute(sample_zip_data, {})

        assert "avg_carbs_g" in result["nutrition"]
        assert "avg_fat_g" in result["nutrition"]
        assert "nutrition_history" in result["nutrition"]
        assert result["nutrition"]["avg_carbs_g"] == 195.0  # (200+190)/2
        assert result["nutrition"]["avg_fat_g"] == 57.5  # (60+55)/2
        history = result["nutrition"]["nutrition_history"]
        assert len(history) == 2
        assert "date" in history[0]
        assert "calories" in history[0]
        assert "protein_g" in history[0]
        assert "carbs_g" in history[0]
        assert "fat_g" in history[0]
        assert "fiber_g" in history[0]
        assert "sodium_mg" in history[0]

    def test_exercise_has_history_and_session_counts(self, sample_zip_data: ZipData) -> None:
        """Exercise includes exercise_history and session_type_counts."""
        result = self.use_case.execute(sample_zip_data, {})

        assert "exercise_history" in result["exercise"]
        assert "session_type_counts" in result["exercise"]
        history = result["exercise"]["exercise_history"]
        assert len(history) == 2
        assert "date" in history[0]
        assert "exercise_minutes" in history[0]
        assert "steps" in history[0]
        assert "exercise_calories" in history[0]
        assert result["exercise"]["session_type_counts"] == {"treadmill": 1, "other": 1}

    def test_comparison_object_present(self, sample_zip_data: ZipData) -> None:
        """Root has comparison object with weight_mfp_kg, weight_withings_kg, steps_mfp, steps_withings."""
        pdf_metrics = {"latest_weight_kg": 83.5, "daily_steps_avg": 7500}
        result = self.use_case.execute(sample_zip_data, pdf_metrics)

        assert "comparison" in result
        comp = result["comparison"]
        assert "weight_mfp_kg" in comp
        assert "weight_withings_kg" in comp
        assert comp["weight_mfp_kg"] == 83.3
        assert comp["weight_withings_kg"] == 83.5
        assert comp["steps_mfp"] == 6500  # avg of 8000, 5000
        assert comp["steps_withings"] == 7500

    def test_weight_includes_body_fat_when_present(self, sample_zip_data_with_extras: ZipData) -> None:
        """Weight section includes body_fat aggregated block when measures have body_fat_pct."""
        result = self.use_case.execute(sample_zip_data_with_extras, {})
        assert "body_fat" in result["weight"]
        bf = result["weight"]["body_fat"]
        assert "average_pct" in bf
        assert "samples" in bf
        assert "min_pct" in bf
        assert "max_pct" in bf
        assert "source_note" in bf
        assert bf["average_pct"] == 22.1  # (22.5 + 22.0 + 21.8) / 3
        assert bf["samples"] == 3
        assert bf["latest_body_fat_pct_raw"] == 21.8

    def test_nutrition_includes_calories_by_meal_and_meal_pattern(
        self, sample_zip_data_with_extras: ZipData
    ) -> None:
        """Nutrition includes calories_by_meal and meal_pattern when nutrition_by_meal exists."""
        result = self.use_case.execute(sample_zip_data_with_extras, {})
        assert "calories_by_meal" in result["nutrition"]
        assert "meal_pattern" in result["nutrition"]
        assert "Café da manhã" in result["nutrition"]["calories_by_meal"]
        assert "Almoço" in result["nutrition"]["calories_by_meal"]

    def test_nutrition_includes_fat_profile_when_present(self, sample_zip_data_with_extras: ZipData) -> None:
        """Nutrition includes fat_profile when fat columns exist."""
        result = self.use_case.execute(sample_zip_data_with_extras, {})
        assert "fat_profile" in result["nutrition"]
        assert "fat_saturated_g" in result["nutrition"]["fat_profile"]

    def test_nutrition_includes_sugar_when_present(self, sample_zip_data_with_extras: ZipData) -> None:
        """Nutrition includes avg_sugar_g and days_high_sugar when sugar_g exists."""
        result = self.use_case.execute(sample_zip_data_with_extras, {})
        assert "avg_sugar_g" in result["nutrition"]
        assert "days_high_sugar" in result["nutrition"]
        assert result["nutrition"]["avg_sugar_g"] == 50.0
        assert result["nutrition"]["days_high_sugar"] >= 1

    def test_returns_weekly_summary(self, sample_zip_data_with_extras: ZipData) -> None:
        """Report includes weekly_summary with averages per week."""
        result = self.use_case.execute(sample_zip_data_with_extras, {})
        assert "weekly_summary" in result
        assert isinstance(result["weekly_summary"], list)

    def test_returns_alerts(self, sample_zip_data_with_extras: ZipData) -> None:
        """Report includes alerts as object with critical, warning, info."""
        result = self.use_case.execute(sample_zip_data_with_extras, {})
        assert "alerts" in result
        assert "critical" in result["alerts"]
        assert "warning" in result["alerts"]
        assert "info" in result["alerts"]

    def test_returns_weekly_adherence(self, sample_zip_data: ZipData) -> None:
        """Report includes weekly_adherence with score, rating, components."""
        result = self.use_case.execute(sample_zip_data, {})
        assert "weekly_adherence" in result
        assert isinstance(result["weekly_adherence"], list)
        if result["weekly_adherence"]:
            w = result["weekly_adherence"][0]
            assert "score" in w
            assert "rating" in w
            assert "components" in w
            assert "calories_score" in w["components"]
            assert "protein_score" in w["components"]
            assert "training_score" in w["components"]
            assert "weekly_targets" in w

    def test_returns_projection(self, sample_zip_data: ZipData) -> None:
        """Report includes projection with scenarios (pessimistic, realistic, optimistic)."""
        result = self.use_case.execute(sample_zip_data, {})
        assert "projection" in result
        p = result["projection"]
        assert "target_date" in p
        assert "method" in p
        assert p["method"] in ("scenario_rates", "trend_from_prev_and_current_week")
        assert "scenarios" in p
        assert "pessimistic" in p["scenarios"]
        assert "realistic" in p["scenarios"]
        assert "optimistic" in p["scenarios"]
        assert "assumptions" in p
        assert "note" in p
        assert "weeks_to_target" in p
        for name in ("pessimistic", "realistic", "optimistic"):
            s = p["scenarios"][name]
            assert "rate_kg_per_week" in s
            assert "projected_ma7_kg" in s

    def test_projection_uses_fallback_rates_when_fewer_than_15_ma7_values(
        self, sample_zip_data: ZipData
    ) -> None:
        """With < 15 MA7 values, projection uses fixed fallback rates and method 'scenario_rates'."""
        result = self.use_case.execute(sample_zip_data, {}, target_date="2026-03-27")
        p = result["projection"]
        assert p["method"] == "scenario_rates"
        rates = p["assumptions"]["scenario_rates_kg_per_week"]
        assert rates["pessimistic"] == -0.14
        assert rates["realistic"] == -0.25
        assert rates["optimistic"] == -0.35
        for name in ("pessimistic", "realistic", "optimistic"):
            s = p["scenarios"][name]
            assert "rate_kg_per_week" in s
            assert "projected_ma7_kg" in s

    def test_projection_uses_trend_rates_when_15_or_more_ma7_values(
        self, zip_data_15_days: ZipData
    ) -> None:
        """With 15+ MA7 values, projection uses trend_from_prev_and_current_week."""
        result = self.use_case.execute(zip_data_15_days, {}, target_date="2026-03-27")
        p = result["projection"]
        assert p["method"] == "trend_from_prev_and_current_week"
        assert "prev_week_rate" in p["assumptions"]
        assert "current_week_rate" in p["assumptions"]
        assert "avg_rate" in p["assumptions"]
        assert "pessimistic" in p["scenarios"]
        assert "realistic" in p["scenarios"]
        assert "optimistic" in p["scenarios"]

    def test_projection_scenarios_ordered_optimistic_le_realistic_le_pessimistic(
        self, zip_data_15_days: ZipData
    ) -> None:
        """Rates must satisfy optimistic <= realistic <= pessimistic (ascending)."""
        result = self.use_case.execute(zip_data_15_days, {}, target_date="2026-03-27")
        p = result["projection"]
        ro = p["scenarios"]["optimistic"]["rate_kg_per_week"]
        rr = p["scenarios"]["realistic"]["rate_kg_per_week"]
        rp = p["scenarios"]["pessimistic"]["rate_kg_per_week"]
        assert ro <= rr <= rp

    def test_projection_trend_rates_computed_from_prev_and_current_week_ma7(
        self, zip_data_15_days: ZipData
    ) -> None:
        """Rates derived from MA7[-1]-MA7[-8] and MA7[-8]-MA7[-15], plus their average."""
        result = self.use_case.execute(zip_data_15_days, {}, target_date="2026-03-27")
        p = result["projection"]
        assert p["method"] == "trend_from_prev_and_current_week"
        current = p["current_ma7_kg"]
        weeks = p["weeks_to_target"]
        for name, s in p["scenarios"].items():
            rate = s["rate_kg_per_week"]
            proj = s["projected_ma7_kg"]
            expected = round(current + rate * weeks, 2)
            assert proj == expected, f"{name}: expected {expected}, got {proj}"

    def test_projection_handles_weight_gain_positive_rates(
        self, zip_data_15_days_upward: ZipData
    ) -> None:
        """When trend is upward, rates are positive; optimistic = slowest gain, pessimistic = fastest gain."""
        result = self.use_case.execute(zip_data_15_days_upward, {}, target_date="2026-03-27")
        p = result["projection"]
        ro = p["scenarios"]["optimistic"]["rate_kg_per_week"]
        rr = p["scenarios"]["realistic"]["rate_kg_per_week"]
        rp = p["scenarios"]["pessimistic"]["rate_kg_per_week"]
        assert ro <= rr <= rp
        assert rp >= 0, "Pessimistic (fastest gain) should be non-negative when gaining"
        proj_pessimistic = p["scenarios"]["pessimistic"]["projected_ma7_kg"]
        current = p["current_ma7_kg"]
        assert proj_pessimistic >= current, "Projected weight should be >= current when gaining"

    def test_projection_note_reflects_rate_range(self, zip_data_15_days: ZipData) -> None:
        """Note mentions the rate range used (dynamic or fallback)."""
        result = self.use_case.execute(zip_data_15_days, {}, target_date="2026-03-27")
        p = result["projection"]
        assert "note" in p
        assert "kg/sem" in p["note"]

    def test_returns_retention_flag(self, sample_zip_data: ZipData) -> None:
        """Report includes retention_flag with is_probable_retention."""
        result = self.use_case.execute(sample_zip_data, {})
        assert "retention_flag" in result
        assert "is_probable_retention" in result["retention_flag"]

    def test_build_pdf_report_v2_returns_structure(self) -> None:
        """build_pdf_report_v2 returns structure with activity, body, sleep, cardio blocks."""
        flat = {}
        result = build_pdf_report_v2(flat)
        assert "activity" in result
        assert "body" in result
        assert "sleep" in result
        assert "cardio" in result
        assert isinstance(result["activity"], dict)
        assert isinstance(result["body"], dict)
        assert isinstance(result["sleep"], dict)
        assert isinstance(result["cardio"], dict)

    def test_build_pdf_report_v2_derives_fat_lean_pct(self) -> None:
        """build_pdf_report_v2 computes derived_fat_mass_pct and derived_lean_mass_pct from mass values."""
        flat = {
            "latest_weight_kg": 90.5,
            "fat_mass_kg": 19.8,
            "lean_mass_kg": 69.1,
        }
        result = build_pdf_report_v2(flat)
        assert result["body"]["derived_fat_mass_pct"] == pytest.approx(21.9, abs=0.1)
        assert result["body"]["derived_lean_mass_pct"] == pytest.approx(76.4, abs=0.1)

    def test_build_report_includes_pdf_report_v2(self, sample_zip_data: ZipData) -> None:
        """Report includes pdf_report_v2 with activity, body, sleep, cardio when pdf_metrics provided."""
        pdf_metrics = {"latest_weight_kg": 90.5, "fat_mass_kg": 19.8, "daily_steps_avg": 18369}
        result = self.use_case.execute(sample_zip_data, pdf_metrics)
        assert "pdf_report_v2" in result
        v2 = result["pdf_report_v2"]
        assert "activity" in v2
        assert "body" in v2
        assert "sleep" in v2
        assert "cardio" in v2

    def test_meta_includes_adherence_targets(self, sample_zip_data: ZipData) -> None:
        """Report meta includes adherence_targets when user_info provided."""
        user_info = {"height_cm": 175, "sex": "M", "age": 35}
        result = self.use_case.execute(sample_zip_data, {}, user_info=user_info)
        assert "meta" in result
        assert "adherence_targets" in result["meta"]
        targets = result["meta"]["adherence_targets"]
        assert "calorie_range" in targets
        assert "protein_g" in targets
        assert "fiber_g" in targets

    def test_personalized_protein_target_from_weight(self, sample_zip_data: ZipData) -> None:
        """Adherence targets use weight from measures when no weight_kg in user_info."""
        # sample_zip_data last weight = 83.3 kg -> protein target ~150
        result = self.use_case.execute(
            sample_zip_data, {}, user_info={"height_cm": 175, "sex": "M", "age": 35}
        )
        targets = result["meta"]["adherence_targets"]
        assert targets["protein_g"] == 150  # 83.3 * 1.8 = 149.94 -> 150

    def test_user_info_weight_override_used_for_targets(self, sample_zip_data: ZipData) -> None:
        """When weight_kg in user_info, it overrides measures weight for target calculation."""
        user_info = {"weight_kg": 67.0, "height_cm": 165, "sex": "F", "age": 30}
        result = self.use_case.execute(sample_zip_data, {}, user_info=user_info)
        targets = result["meta"]["adherence_targets"]
        assert targets["protein_g"] == 121  # 67 * 1.8

    def test_user_info_override_protein_in_targets(self, sample_zip_data: ZipData) -> None:
        """user_info protein_g override is applied to adherence targets."""
        user_info = {"protein_g": 100, "height_cm": 175, "sex": "M", "age": 35}
        result = self.use_case.execute(sample_zip_data, {}, user_info=user_info)
        targets = result["meta"]["adherence_targets"]
        assert targets["protein_g"] == 100

    def test_user_info_override_fat_and_carbs_in_targets(self, sample_zip_data: ZipData) -> None:
        """user_info fat_g and carbs_g overrides are applied to adherence targets."""
        user_info = {"fat_g": 65, "carbs_g": 150, "height_cm": 175, "sex": "M", "age": 35}
        result = self.use_case.execute(sample_zip_data, {}, user_info=user_info)
        targets = result["meta"]["adherence_targets"]
        assert targets["fat_g"] == 65
        assert targets["carbs_g"] == 150

    def test_weekly_adherence_uses_personalized_targets(self, sample_zip_data: ZipData) -> None:
        """Weekly adherence weekly_targets reflect personalized targets."""
        user_info = {"weight_kg": 67.0, "height_cm": 165, "sex": "F", "age": 30}
        result = self.use_case.execute(sample_zip_data, {}, user_info=user_info)
        if result["weekly_adherence"]:
            w = result["weekly_adherence"][0]
            assert w["weekly_targets"]["protein_g"] == 121
            assert w["weekly_targets"]["calorie_range"][0] < 1800  # Sibele gets lower calories

    def test_nutrition_summary_includes_adherence_targets(self, sample_zip_data: ZipData) -> None:
        """Nutrition summary includes adherence_targets and calorie thresholds."""
        user_info = {"height_cm": 175, "sex": "M", "age": 35}
        result = self.use_case.execute(sample_zip_data, {}, user_info=user_info)
        nut = result["nutrition"]
        assert "adherence_targets" in nut
        assert "calorie_low_threshold" in nut
        assert "calorie_high_threshold" in nut
