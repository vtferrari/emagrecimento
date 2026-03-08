"""Adherence targets computation and projection constants."""

from __future__ import annotations

from typing import Any

# Default adherence targets (used when user_info insufficient for personalized calc)
ADHERENCE_TARGETS = {
    "calorie_range": [1800, 1950],
    "protein_g": 170,
    "fat_g": None,
    "carbs_g": None,
    "fiber_g": 25,
    "sodium_mg_max": 2500,
    "sessions_per_week": 4,
}

# Fallback scenario rates when insufficient MA7 data (need 15+ days for trend)
PROJECTION_FALLBACK_RATES_KG_PER_WEEK = {
    "pessimistic": -0.14,
    "realistic": -0.25,
    "optimistic": -0.35,
}
MIN_MA7_ROWS_FOR_TREND = 15


def compute_adherence_targets(
    weight_kg: float,
    height_cm: int | None = None,
    sex: str | None = None,
    age: int | None = None,
    *,
    override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Compute personalized adherence targets from weight, height, sex, age.
    Uses Mifflin-St Jeor for BMR, 1.8 g/kg protein (cutting), 14g fiber/1000 kcal.
    override: optional dict with calorie_min, calorie_max, protein_g, fat_g, carbs_g, fiber_g
    to override specific fields; non-overridden fields remain personalized.
    """
    targets: dict[str, Any] = dict(ADHERENCE_TARGETS)

    # Protein: 1.8 g/kg body weight (scientific consensus for cutting - preserve lean mass)
    protein_g = max(80, min(200, round(weight_kg * 1.8, 0)))
    targets["protein_g"] = int(protein_g)

    # Calories: Mifflin-St Jeor BMR, then TDEE * 0.85 for ~15% deficit
    if height_cm is not None and sex and age is not None:
        if sex.upper() == "M":
            bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
        else:
            bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
        tdee = bmr * 1.375  # light activity
        cutting_cal = round(tdee * 0.85)
        margin = max(75, int(cutting_cal * 0.05))
        targets["calorie_range"] = [
            max(1200, cutting_cal - margin),
            min(3000, cutting_cal + margin),
        ]

    # Fiber: 14g per 1000 kcal (ADA) or min 20g
    cal_mid = (targets["calorie_range"][0] + targets["calorie_range"][1]) / 2
    fiber_g = max(20, round(14 * cal_mid / 1000, 0))
    targets["fiber_g"] = int(fiber_g)

    # Apply overrides on top of personalized targets (override takes precedence per field)
    if override:
        if "calorie_min" in override and override["calorie_min"] is not None:
            targets["calorie_range"] = [
                int(override["calorie_min"]),
                targets["calorie_range"][1],
            ]
        if "calorie_max" in override and override["calorie_max"] is not None:
            targets["calorie_range"] = [
                targets["calorie_range"][0],
                int(override["calorie_max"]),
            ]
        if "protein_g" in override and override["protein_g"] is not None:
            targets["protein_g"] = int(override["protein_g"])
        if "fat_g" in override and override["fat_g"] is not None:
            targets["fat_g"] = int(override["fat_g"])
        if "carbs_g" in override and override["carbs_g"] is not None:
            targets["carbs_g"] = int(override["carbs_g"])
        if "fiber_g" in override and override["fiber_g"] is not None:
            targets["fiber_g"] = int(override["fiber_g"])

    return targets
