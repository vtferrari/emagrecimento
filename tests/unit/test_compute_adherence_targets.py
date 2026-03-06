"""Unit tests for compute_adherence_targets."""

import pytest

from emagrecimento.application.use_cases.build_report import (
    ADHERENCE_TARGETS,
    compute_adherence_targets,
)


class TestComputeAdherenceTargets:
    """Tests for compute_adherence_targets function."""

    def test_weight_only_uses_default_calories_and_computes_protein(self) -> None:
        """With only weight, protein is computed (1.8 g/kg), calories stay default."""
        result = compute_adherence_targets(67.0)
        assert result["protein_g"] == 121  # 67 * 1.8 = 120.6 -> 121
        assert result["calorie_range"] == ADHERENCE_TARGETS["calorie_range"]
        # Fiber = max(20, 14 * cal_mid/1000), cal_mid=1875 -> 26
        assert result["fiber_g"] >= 20
        assert result["sodium_mg_max"] == 2500

    def test_protein_scales_with_weight(self) -> None:
        """Protein target = 1.8 g/kg, clamped 80-200."""
        assert compute_adherence_targets(50.0)["protein_g"] == 90
        assert compute_adherence_targets(67.0)["protein_g"] == 121
        assert compute_adherence_targets(90.0)["protein_g"] == 162
        assert compute_adherence_targets(120.0)["protein_g"] == 200  # capped

    def test_protein_floor_at_80g(self) -> None:
        """Very light weight still gets minimum 80g protein."""
        result = compute_adherence_targets(40.0)
        assert result["protein_g"] == 80

    def test_full_params_computes_calories_male(self) -> None:
        """With height, sex, age: calories computed via Mifflin-St Jeor (male)."""
        result = compute_adherence_targets(
            90.0, height_cm=180, sex="M", age=35
        )
        # BMR = 10*90 + 6.25*180 - 5*35 + 5 = 900 + 1125 - 175 + 5 = 1855
        # TDEE = 1855 * 1.375 = 2550.6, cutting = 2550.6 * 0.85 = 2168
        assert 1900 <= result["calorie_range"][0] <= 2200
        assert 2000 <= result["calorie_range"][1] <= 2400
        assert result["protein_g"] == 162
        assert result["fiber_g"] >= 20

    def test_full_params_computes_calories_female(self) -> None:
        """With height, sex, age: calories computed via Mifflin-St Jeor (female)."""
        result = compute_adherence_targets(
            67.0, height_cm=165, sex="F", age=30
        )
        # BMR = 10*67 + 6.25*165 - 5*30 - 161 = 670 + 1031 - 150 - 161 = 1390
        # TDEE = 1390 * 1.375 = 1911, cutting = 1911 * 0.85 = 1624
        assert 1400 <= result["calorie_range"][0] <= 1750
        assert 1500 <= result["calorie_range"][1] <= 1850
        assert result["protein_g"] == 121

    def test_sibele_vs_vini_different_protein_targets(self) -> None:
        """Sibele (67kg) and Vini (90kg) get different protein targets."""
        sibele = compute_adherence_targets(67.0)
        vini = compute_adherence_targets(90.0)
        assert sibele["protein_g"] == 121
        assert vini["protein_g"] == 162
        assert sibele["protein_g"] < vini["protein_g"]

    def test_override_protein(self) -> None:
        """Override protein_g when provided."""
        result = compute_adherence_targets(67.0, override={"protein_g": 100})
        assert result["protein_g"] == 100
        assert result["calorie_range"] == ADHERENCE_TARGETS["calorie_range"]

    def test_override_calorie_range(self) -> None:
        """Override calorie_min and calorie_max when provided."""
        result = compute_adherence_targets(
            67.0,
            override={"calorie_min": 1400, "calorie_max": 1600},
        )
        assert result["calorie_range"] == [1400, 1600]

    def test_override_fiber(self) -> None:
        """Override fiber_g when provided."""
        result = compute_adherence_targets(67.0, override={"fiber_g": 30})
        assert result["fiber_g"] == 30

    def test_override_fat(self) -> None:
        """Override fat_g when provided."""
        result = compute_adherence_targets(67.0, override={"fat_g": 65})
        assert result["fat_g"] == 65

    def test_override_carbs(self) -> None:
        """Override carbs_g when provided."""
        result = compute_adherence_targets(67.0, override={"carbs_g": 150})
        assert result["carbs_g"] == 150

    def test_override_takes_precedence_over_computed(self) -> None:
        """When override is provided, no BMR/protein computation is done."""
        result = compute_adherence_targets(
            90.0,
            height_cm=180,
            sex="M",
            age=35,
            override={"protein_g": 150, "calorie_min": 1800, "calorie_max": 2000},
        )
        assert result["protein_g"] == 150
        assert result["calorie_range"] == [1800, 2000]

    def test_fiber_scales_with_calories_when_no_override(self) -> None:
        """Fiber = max(20, 14 * cal_mid/1000) when calories are computed."""
        # Low calorie target -> lower fiber
        low_cal = compute_adherence_targets(55.0, height_cm=160, sex="F", age=25)
        cal_mid = (low_cal["calorie_range"][0] + low_cal["calorie_range"][1]) / 2
        expected_fiber = max(20, round(14 * cal_mid / 1000, 0))
        assert low_cal["fiber_g"] == int(expected_fiber)

    def test_returns_all_required_keys(self) -> None:
        """Result has calorie_range, protein_g, fat_g, carbs_g, fiber_g, sodium_mg_max, sessions_per_week."""
        result = compute_adherence_targets(70.0)
        assert "calorie_range" in result
        assert len(result["calorie_range"]) == 2
        assert "protein_g" in result
        assert "fat_g" in result
        assert "carbs_g" in result
        assert "fiber_g" in result
        assert "sodium_mg_max" in result
        assert "sessions_per_week" in result
