"""Serialize WithingsHealthRecord to JSON-safe dict for API response."""

from __future__ import annotations

from typing import Any

from emagrecimento.domain.withings_zip import WithingsHealthRecord


def withings_health_record_to_dict(record: WithingsHealthRecord) -> dict[str, Any]:
    """Convert WithingsHealthRecord to JSON-serializable dict matching API spec."""
    body = record.body_snapshots
    first_body = body[0] if body else None
    latest_body = body[-1] if body else None

    body_composition: dict[str, Any] = {}
    if latest_body:
        body_composition["latest"] = {
            "date": latest_body.date,
            "weight_kg": round(latest_body.weight_kg, 2),
            "fat_mass_kg": round(latest_body.fat_mass_kg, 2),
            "fat_mass_pct": record.fat_mass_pct,
            "muscle_mass_kg": round(latest_body.muscle_mass_kg, 2),
            "bone_mass_kg": round(latest_body.bone_mass_kg, 2) if latest_body.bone_mass_kg is not None else None,
            "water_pct": round(latest_body.water_pct, 1) if latest_body.water_pct is not None else None,
            "visceral_fat": round(latest_body.visceral_fat, 2),
            "bmr_kcal": latest_body.bmr_kcal,
            "metabolic_age": latest_body.metabolic_age,
            "fat_free_mass_kg": round(latest_body.fat_free_mass_kg, 2) if latest_body.fat_free_mass_kg is not None else None,
        }
    if first_body and first_body != latest_body:
        body_composition["first"] = {
            "date": first_body.date,
            "weight_kg": round(first_body.weight_kg, 2),
            "fat_mass_kg": round(first_body.fat_mass_kg, 2),
            "fat_mass_pct": round(100 * first_body.fat_mass_kg / first_body.weight_kg, 1) if first_body.weight_kg > 0 else None,
            "muscle_mass_kg": round(first_body.muscle_mass_kg, 2),
            "bone_mass_kg": round(first_body.bone_mass_kg, 2) if first_body.bone_mass_kg is not None else None,
            "water_pct": round(first_body.water_pct, 1) if first_body.water_pct is not None else None,
            "visceral_fat": round(first_body.visceral_fat, 2),
            "bmr_kcal": first_body.bmr_kcal,
            "metabolic_age": first_body.metabolic_age,
            "fat_free_mass_kg": round(first_body.fat_free_mass_kg, 2) if first_body.fat_free_mass_kg is not None else None,
        }
    if record.delta_weight is not None and first_body and latest_body:
        bmr_delta = None
        if first_body.bmr_kcal is not None and latest_body.bmr_kcal is not None:
            bmr_delta = latest_body.bmr_kcal - first_body.bmr_kcal
        body_composition["delta"] = {
            "weight_kg": record.delta_weight,
            "fat_mass_kg": record.delta_fat_mass,
            "muscle_mass_kg": record.delta_muscle_mass,
            "visceral_fat": record.delta_visceral_fat,
            "bmr_kcal": bmr_delta,
            "metabolic_age": record.delta_metabolic_age,
        }
    body_composition["history"] = [
        {
            "date": s.date,
            "weight_kg": round(s.weight_kg, 2),
            "fat_mass_kg": round(s.fat_mass_kg, 2),
            "muscle_mass_kg": round(s.muscle_mass_kg, 2),
            "visceral_fat": round(s.visceral_fat, 2),
            "metabolic_age": s.metabolic_age,
        }
        for s in body
    ]

    # Cardiovascular: HR, SpO2, PWV, ECG from measures + ECG files
    hr_vals = [(s.date, None) for s in body]  # Measures may have Heart rate
    # For now, use ECG HR if available
    hr_history: list[dict[str, Any]] = []
    hr_values: list[int] = []
    for e in record.ecg_readings:
        hr_history.append({"date": e.date, "value": e.hr})
        hr_values.append(e.hr)
    cardiovascular: dict[str, Any] = {
        "heart_rate": {
            "mean": round(sum(hr_values) / len(hr_values), 1) if hr_values else None,
            "min": min(hr_values) if hr_values else None,
            "max": max(hr_values) if hr_values else None,
            "history": hr_history,
        },
        "spo2": {"mean": None, "min": None, "history": []},
        "pwv": {"mean": None, "history": []},
        "vascular_age": {"latest": None, "history": []},
        "afib": {"total": len(record.ecg_readings), "normal": sum(1 for e in record.ecg_readings if e.value == 9), "abnormal": sum(1 for e in record.ecg_readings if e.value != 9)},
        "blood_pressure": None,
        "ecg_summary": {
            "total": len(record.ecg_readings),
            "hr_mean": round(sum(hr_values) / len(hr_values), 1) if hr_values else None,
            "hr_min": min(hr_values) if hr_values else None,
            "hr_max": max(hr_values) if hr_values else None,
            "normal": sum(1 for e in record.ecg_readings if e.value == 9),
        } if record.ecg_readings else None,
    }

    # Sleep summary
    nights = record.sleep_nights
    sleep_summary: dict[str, Any] = {}
    if nights:
        nights_with_hr = [n for n in nights if n.hr_avg > 0]
        avg_hr_mean_val = (
            round(sum(n.hr_avg for n in nights_with_hr) / len(nights_with_hr), 1)
            if nights_with_hr
            else None
        )
        sleep_summary = {
            "total_nights": len(nights),
            "avg_total_h": record.avg_sleep_h,
            "avg_light_h": round(sum(n.light_h for n in nights) / len(nights), 1),
            "avg_deep_h": round(sum(n.deep_h for n in nights) / len(nights), 1),
            "avg_rem_h": round(sum(n.rem_h for n in nights) / len(nights), 1),
            "avg_awake_h": round(sum(n.awake_h for n in nights) / len(nights), 1),
            "avg_hr_min": round(sum(n.hr_min for n in nights) / len(nights), 1),
            "avg_hr_max": round(sum(n.hr_max for n in nights) / len(nights), 1),
            "avg_hr_mean": avg_hr_mean_val,
        }
    sleep_history = [
        {
            "date": n.date,
            "total_h": n.total_h,
            "light_h": n.light_h,
            "deep_h": n.deep_h,
            "rem_h": n.rem_h,
            "awake_h": n.awake_h,
            "hr_min": n.hr_min,
            "hr_max": n.hr_max,
            "hr_avg": n.hr_avg,
        }
        for n in nights
    ]

    # Activity
    activity_days = record.activity_days
    activity_summary: dict[str, Any] = {}
    if activity_days:
        activity_summary = {
            "days_tracked": len(activity_days),
            "avg_daily_steps": int(record.avg_daily_steps) if record.avg_daily_steps is not None else None,
        }
    activity_history = [{"date": a.date, "steps": a.steps} for a in activity_days]

    return {
        "body_composition": body_composition,
        "cardiovascular": cardiovascular,
        "sleep": {"summary": sleep_summary, "history": sleep_history},
        "activity": {"summary": activity_summary, "history": activity_history},
    }
