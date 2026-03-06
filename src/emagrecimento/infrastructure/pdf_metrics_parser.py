"""Withings PDF metrics parser adapter."""

from __future__ import annotations

import re
from typing import Any

from emagrecimento.application.interfaces import IPdfMetricsParser
from emagrecimento.domain.value_objects import parse_number, parse_duration_minutes


class WithingsPdfMetricsParser(IPdfMetricsParser):
    """Parse Withings medical report PDF text into metrics dict."""

    # Primary patterns (strict)
    PATTERNS = {
        "report_period": r"Overview\s*[·\-\u00b7]\s*([0-9]{1,2}\s+[A-Za-z]{3}\s*-\s*[0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})",
        "latest_weight_kg": r"Weight\s+([0-9]+(?:\.[0-9]+)?)\s*kg\s+(?:Latest|Latest\s+Weight)",
        "weight_trend_kg": r"Weight\s+[0-9]+(?:\.[0-9]+)?\s*kg\s+(?:Latest\s+)?([+-]?[0-9]+(?:\.[0-9]+)?)\s*kg\s+Trend",
        "bmr_kcal": r"BMR\s+([0-9,]+)\s*kcal\s+(?:Latest|Average)",
        "fat_mass_kg": r"Fat\s+Mass\s+([0-9]+(?:\.[0-9]+)?)\s*kg\s+(?:Latest|Average)",
        "fat_mass_trend_kg": r"Fat\s+Mass\s+[0-9]+(?:\.[0-9]+)?\s*kg\s+(?:Latest\s+)?([+-]?[0-9]+(?:\.[0-9]+)?)\s*kg\s+Trend",
        "muscle_mass_kg": r"Muscle\s+Mass\s+([0-9]+(?:\.[0-9]+)?)\s*kg\s+(?:Latest|Average)",
        "muscle_mass_trend_kg": r"Muscle\s+Mass\s+[0-9]+(?:\.[0-9]+)?\s*kg\s+(?:Latest\s+)?([+-]?[0-9]+(?:\.[0-9]+)?)\s*kg\s+Trend",
        "lean_mass_kg": r"Lean\s+Mass\s+([0-9]+(?:\.[0-9]+)?)\s*kg\s+(?:Latest|Average)",
        "lean_mass_trend_kg": r"Lean\s+Mass\s+[0-9]+(?:\.[0-9]+)?\s*kg\s+(?:Latest\s+)?([+-]?[0-9]+(?:\.[0-9]+)?)\s*kg\s+Trend",
        "daily_steps_avg": r"Daily\s+Steps\s+([0-9,]+)\s*steps?\s+(?:Average|Latest)",
        # Match "1h10" (1h10min) or plain "70" (minutes)
        "daily_active_minutes_avg": r"(?:Daily\s+)?Active\s+Minutes\s+([0-9]+h[0-9]{2}|[0-9,]+)\s*(?:min|minutes?)?\s*(?:Average|Latest)?",
        # Sleep: prefer "Sleep Duration Average 7h13" (Withings format) or "Sleep Duration 7h30 Average"
        "sleep_avg": r"Sleep\s+Duration\s+(?:Average\s+)?([0-9]+h[0-9]{2})(?:\s+Average)?",
        "total_sleep_time": r"Total\s+Sleep\s+Time\s*\(TST\)\s*([0-9]+h[0-9]{2})",
        "sleep_efficiency_pct": r"([0-9]+)\s*%\s+Efficiency",
        "water_mass_kg": r"Water\s+Mass\s+([0-9]+(?:\.[0-9]+)?)\s*kg",
        "bone_mass_kg": r"Bone\s+Mass\s+([0-9]+(?:\.[0-9]+)?)\s*kg",
        "visceral_fat": r"Visceral\s+Fat\s+([0-9]+(?:\.[0-9]+)?)",
        "days_over_10k_pct": r"([0-9]+)\s*%\s*(?:of\s+)?days?\s+(?:above|over)\s+10k",
        "days_under_2k_pct": r"([0-9]+)\s*%\s*(?:of\s+)?days?\s+(?:below|under)\s+2k",
        "nights_over_7h_pct": r"([0-9]+)\s*%\s*(?:of\s+)?nights?\s+(?:above|over)\s+7h",
        "nights_under_5h_pct": r"([0-9]+)\s*%\s*(?:of\s+)?nights?\s+(?:below|under)\s+5h",
        "sleep_latency_sec": r"(?:Sleep\s+)?Latency\s+([0-9]+)\s*(?:sec|s\b)",
        "snoring_min": r"Snoring\s+([0-9]+)\s*min",
        "overnight_hr_bpm": r"(?:Overnight|Night)\s+(?:Heart\s+Rate|HR)\s+([0-9]+)\s*bpm",
        "awake_hr_avg_bpm": r"Awake\s+(?:Heart\s+Rate|HR)\s+([0-9]+)\s*bpm",
        "asleep_hr_avg_bpm": r"Asleep\s+(?:Heart\s+Rate|HR)\s+([0-9]+)\s*bpm",
        "pwv_m_per_s": r"PWV\s+([0-9]+(?:\.[0-9]+)?)\s*m/s",
        "awake_spo2_avg_pct": r"SpO2\s+(?:avg|average)?\s*([0-9]+)\s*%",
        "awake_spo2_min_pct": r"SpO2\s+min(?:imum)?\s+([0-9]+)\s*%",
        "measurements_under_90_pct": r"([0-9]+)\s+measurements?\s+(?:below|under)\s+90",
        "time_in_bed": r"Time\s+in\s+Bed\s*\(TIB\)?\s*([0-9]+h[0-9]{2})",
        "nights": r"([0-9]+)\s+nights?",
        "bmi_avg": r"BMI\s+([0-9]+(?:\.[0-9]+)?)\s*(?:Average|Latest)?",
        # User demographics (for auto-filling form)
        "age_years": r"(?:^|\s)([0-9]{1,3})\s*yo\b",
        "biological_sex": r"Biological\s+Sex:\s*(Female|Male)",
    }

    # Fallback patterns (more permissive when primary fails)
    FALLBACK_PATTERNS = {
        "weight_trend_kg": r"([+-]?[0-9]+(?:\.[0-9]+)?)\s*kg\s+Trend",
        "fat_mass_trend_kg": r"Fat\s+Mass.*?([+-]?[0-9]+(?:\.[0-9]+)?)\s*kg\s+Trend",
        "muscle_mass_trend_kg": r"Muscle\s+Mass.*?([+-]?[0-9]+(?:\.[0-9]+)?)\s*kg\s+Trend",
        "lean_mass_trend_kg": r"Lean\s+Mass.*?([+-]?[0-9]+(?:\.[0-9]+)?)\s*kg\s+Trend",
        "daily_active_minutes_avg": r"Active\s+Minutes\s+([0-9]+h[0-9]{2}|[0-9,]+)",
        "sleep_avg": r"Sleep\s+.*?([0-9]+h[0-9]{2})\s+(?:Average|Weekdays)",
        "sleep_efficiency_pct": r"Sleep\s+Efficiency\s+([0-9]+)(?!\d)\s*%",
        "days_over_10k_pct": r"([0-9]+)\s*%\s+above\s+10k",
        "nights_over_7h_pct": r"([0-9]+)\s*%\s+above\s+7h",
        "overnight_hr_bpm": r"Heart\s+Rate\s+(?:overnight|night)\s+([0-9]+)\s*bpm",
        "pwv_m_per_s": r"Pulse\s+Wave\s+Velocity\s+([0-9]+(?:\.[0-9]+)?)",
        "awake_spo2_avg_pct": r"SpO2\s+([0-9]+)\s*%",
        "time_in_bed": r"([0-9]+h[0-9]{2})\s+Time\s+in\s+Bed",
        "total_sleep_time": r"([0-9]+h[0-9]{2})\s+Total\s+Sleep\s+Time",
    }

    def parse(self, text: str) -> dict[str, Any]:
        text = re.sub(r"\s+", " ", text)
        result: dict[str, Any] = {}

        for key, pattern in self.PATTERNS.items():
            match = re.search(pattern, text, flags=re.IGNORECASE)
            result[key] = match.group(1) if match else None

        # Try fallbacks for keys that are still None
        for key, pattern in self.FALLBACK_PATTERNS.items():
            if result.get(key) is None:
                match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
                result[key] = match.group(1) if match else None

        for key in list(result.keys()):
            if result[key] is None:
                continue
            # Keep sleep/time values as string (e.g. "7h30") - they have time format
            if key in ("sleep_avg", "total_sleep_time", "time_in_bed") and "h" in str(result[key]):
                continue
            # Daily active minutes can be "1h10" (1h10min) - convert to minutes
            if key == "daily_active_minutes_avg" and "h" in str(result[key]):
                parsed = parse_duration_minutes(result[key])
                result[key] = int(parsed) if parsed is not None else result[key]
                continue
            if (
                key.endswith("_kg")
                or key.endswith("_kcal")
                or key.endswith("_pct")
                or key.endswith("_avg")
                or key.endswith("_bpm")
                or key.endswith("_sec")
                or key.endswith("_min")
                or key in ("visceral_fat", "nights", "pwv_m_per_s", "age_years")
            ):
                parsed = parse_number(result[key])
                result[key] = parsed if parsed is not None else result[key]
            if key == "biological_sex":
                val = str(result[key]).strip().lower()
                result[key] = "F" if val == "female" else "M" if val == "male" else None

        return result
