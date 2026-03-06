"""Transform flat PDF metrics into structured v2 report with activity, body, sleep, cardio blocks."""

from __future__ import annotations

from typing import Any


def build_pdf_report_v2(flat: dict[str, Any]) -> dict[str, Any]:
    """Transform flat PDF metrics into structured v2 with activity, body, sleep, cardio blocks."""
    activity: dict[str, Any] = {}
    body: dict[str, Any] = {}
    sleep: dict[str, Any] = {}
    cardio: dict[str, Any] = {}

    # Activity: map from flat keys
    if flat.get("daily_steps_avg") is not None:
        activity["avg_daily_steps"] = int(flat["daily_steps_avg"])
    if flat.get("daily_active_minutes_avg") is not None:
        activity["avg_active_minutes"] = int(flat["daily_active_minutes_avg"])
    if flat.get("days_over_10k_pct") is not None:
        activity["days_over_10k_pct"] = int(flat["days_over_10k_pct"])
    if flat.get("days_under_2k_pct") is not None:
        activity["days_under_2k_pct"] = int(flat["days_under_2k_pct"])

    # Body: map from flat keys and compute derived percentages
    weight_kg = flat.get("latest_weight_kg")
    fat_mass = flat.get("fat_mass_kg")
    lean_mass = flat.get("lean_mass_kg")
    if weight_kg is not None:
        body["latest_weight_kg"] = round(float(weight_kg), 2)
    if flat.get("bmi_avg") is not None:
        body["bmi_avg"] = round(float(flat["bmi_avg"]), 1)
    if flat.get("bmr_kcal") is not None:
        body["bmr_kcal"] = int(flat["bmr_kcal"])
    if fat_mass is not None:
        body["fat_mass_kg"] = round(float(fat_mass), 2)
    if flat.get("muscle_mass_kg") is not None:
        body["muscle_mass_kg"] = round(float(flat["muscle_mass_kg"]), 2)
    if lean_mass is not None:
        body["lean_mass_kg"] = round(float(lean_mass), 2)
    if flat.get("water_mass_kg") is not None:
        body["water_mass_kg"] = round(float(flat["water_mass_kg"]), 2)
    if flat.get("bone_mass_kg") is not None:
        body["bone_mass_kg"] = round(float(flat["bone_mass_kg"]), 2)
    if flat.get("visceral_fat") is not None:
        body["visceral_fat"] = round(float(flat["visceral_fat"]), 2)
    if weight_kg and weight_kg > 0 and fat_mass is not None:
        body["derived_fat_mass_pct"] = round(100 * float(fat_mass) / float(weight_kg), 1)
    if weight_kg and weight_kg > 0 and lean_mass is not None:
        body["derived_lean_mass_pct"] = round(100 * float(lean_mass) / float(weight_kg), 1)

    # Sleep
    if flat.get("sleep_avg"):
        sleep["total_sleep_time"] = flat["sleep_avg"]
    if flat.get("sleep_efficiency_pct") is not None:
        sleep["efficiency_pct"] = int(flat["sleep_efficiency_pct"])
    if flat.get("nights_over_7h_pct") is not None:
        sleep["nights_over_7h_pct"] = int(flat["nights_over_7h_pct"])
    if flat.get("nights_under_5h_pct") is not None:
        sleep["nights_under_5h_pct"] = int(flat["nights_under_5h_pct"])
    if flat.get("time_in_bed"):
        sleep["time_in_bed"] = flat["time_in_bed"]
    if flat.get("sleep_latency_sec") is not None:
        sleep["sleep_latency_sec"] = int(flat["sleep_latency_sec"])
    if flat.get("snoring_min") is not None:
        sleep["snoring_min"] = int(flat["snoring_min"])
    if flat.get("overnight_hr_bpm") is not None:
        sleep["overnight_hr_bpm"] = int(flat["overnight_hr_bpm"])
    if flat.get("nights") is not None:
        sleep["nights"] = int(flat["nights"])

    # Cardio
    if flat.get("awake_hr_avg_bpm") is not None:
        cardio["awake_hr_avg_bpm"] = int(flat["awake_hr_avg_bpm"])
    if flat.get("asleep_hr_avg_bpm") is not None:
        cardio["asleep_hr_avg_bpm"] = int(flat["asleep_hr_avg_bpm"])
    if flat.get("pwv_m_per_s") is not None:
        cardio["pwv_m_per_s"] = round(float(flat["pwv_m_per_s"]), 2)
    if flat.get("awake_spo2_avg_pct") is not None:
        cardio["awake_spo2_avg_pct"] = int(flat["awake_spo2_avg_pct"])
    if flat.get("awake_spo2_min_pct") is not None:
        cardio["awake_spo2_min_pct"] = int(flat["awake_spo2_min_pct"])
    if flat.get("measurements_under_90_pct") is not None:
        cardio["measurements_under_90_pct"] = int(flat["measurements_under_90_pct"])

    result: dict[str, Any] = {
        "activity": activity,
        "body": body,
        "sleep": sleep,
        "cardio": cardio,
    }
    if flat.get("report_period"):
        result["report_period"] = flat["report_period"]
    return result
