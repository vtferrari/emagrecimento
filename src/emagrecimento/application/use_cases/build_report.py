"""Build report summary use case."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from emagrecimento.application.services.adherence_targets import (
    ADHERENCE_TARGETS,
    MIN_MA7_ROWS_FOR_TREND,
    PROJECTION_FALLBACK_RATES_KG_PER_WEEK,
    compute_adherence_targets,
)
from emagrecimento.application.transformers.pdf_report_v2 import build_pdf_report_v2
from emagrecimento.domain.entities import ZipData

# Default target date for projection (configurable later)
DEFAULT_PROJECTION_TARGET = "2026-03-27"


class BuildReportUseCase:
    """Build final report summary from ZipData and PDF metrics."""

    def execute(
        self,
        zip_data: ZipData,
        pdf_metrics: dict[str, Any],
        *,
        target_date: str | None = None,
        user_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build JSON-serializable report (no NaN values)."""
        target_date = target_date or DEFAULT_PROJECTION_TARGET
        user_info = user_info or {}
        measures = zip_data.measures.copy()
        nutrition = zip_data.nutrition_daily.copy()
        exercise = zip_data.exercise_daily.copy()

        latest_rows = measures.tail(15).copy()

        last_n_days = self._build_weight_records(latest_rows)
        weight_history = self._build_weight_records(measures)

        # Body fat (optional): aggregated block only - daily readings are noisy for home bioimpedance
        body_fat_block: dict[str, Any] = {}
        if "body_fat_pct" in measures.columns:
            non_null = measures["body_fat_pct"].dropna()
            if not non_null.empty:
                body_fat_block = {
                    "is_reliable_for_trend": False,
                    "samples": int(len(non_null)),
                    "average_pct": round(float(non_null.mean()), 1),
                    "min_pct": round(float(non_null.min()), 1),
                    "max_pct": round(float(non_null.max()), 1),
                    "source_note": "Daily body fat readings are noisy; use period average only.",
                    "latest_body_fat_pct_raw": round(float(non_null.iloc[-1]), 2),
                }

        latest_weight = float(measures.iloc[-1]["weight"])
        latest_ma5 = float(measures.iloc[-1]["ma5"]) if pd.notna(measures.iloc[-1]["ma5"]) else None
        latest_ma7 = float(measures.iloc[-1]["ma7"]) if pd.notna(measures.iloc[-1]["ma7"]) else None

        first_ma7 = measures["ma7"].dropna().iloc[0] if not measures["ma7"].dropna().empty else None
        last_ma7 = measures["ma7"].dropna().iloc[-1] if not measures["ma7"].dropna().empty else None

        # Personalized adherence targets from weight, height, sex, age
        weight_for_targets = user_info.get("weight_kg")
        if weight_for_targets is None or weight_for_targets == "":
            weight_for_targets = latest_weight
        else:
            weight_for_targets = float(weight_for_targets)
        override = {}
        for k in ("calorie_min", "calorie_max", "protein_g", "fat_g", "carbs_g", "fiber_g"):
            v = user_info.get(k)
            if v is not None and v != "":
                override[k] = int(v)
        adherence_targets = compute_adherence_targets(
            weight_for_targets,
            height_cm=user_info.get("height_cm"),
            sex=user_info.get("sex"),
            age=user_info.get("age"),
            override=override if override else None,
        )
        cal_lo, cal_hi = adherence_targets["calorie_range"]
        protein_target = adherence_targets["protein_g"]
        fiber_target = adherence_targets["fiber_g"]

        nutrition_summary = {
            "days_logged": int(nutrition["date"].nunique()),
            "avg_calories": round(float(nutrition["calories"].mean()), 1),
            "avg_protein_g": round(float(nutrition["protein_g"].mean()), 1),
            "avg_fiber_g": round(float(nutrition["fiber_g"].mean()), 1),
            "avg_sodium_mg": round(float(nutrition["sodium_mg"].mean()), 1),
            "days_1800_to_1950": int(((nutrition["calories"] >= cal_lo) & (nutrition["calories"] <= cal_hi)).sum()),
            "calorie_low_threshold": max(1200, cal_lo - 200),
            "calorie_high_threshold": cal_hi + 250,
            "days_below_1600": int((nutrition["calories"] < max(1200, cal_lo - 200)).sum()),
            "days_above_2200": int((nutrition["calories"] > cal_hi + 250).sum()),
            "days_protein_170_plus": int((nutrition["protein_g"] >= protein_target).sum()),
            "days_fiber_20_plus": int((nutrition["fiber_g"] >= max(15, fiber_target - 5)).sum()),
            "adherence_targets": adherence_targets,
        }
        if "carbs_g" in nutrition.columns:
            nutrition_summary["avg_carbs_g"] = round(float(nutrition["carbs_g"].mean()), 1)
        if "fat_g" in nutrition.columns:
            nutrition_summary["avg_fat_g"] = round(float(nutrition["fat_g"].mean()), 1)

        nutrition_history = self._build_nutrition_history(nutrition)
        nutrition_summary["nutrition_history"] = nutrition_history

        # Sugar (optional)
        if "sugar_g" in nutrition.columns:
            nutrition_summary["avg_sugar_g"] = round(float(nutrition["sugar_g"].mean()), 1)
            nutrition_summary["days_high_sugar"] = int((nutrition["sugar_g"] > 50).sum())

        # Fat profile (optional)
        fat_cols = ["fat_saturated_g", "fat_poly_g", "fat_mono_g"]
        if all(c in nutrition.columns for c in fat_cols) and "fat_g" in nutrition.columns:
            total_fat = nutrition["fat_g"].sum()
            nutrition_summary["fat_profile"] = {
                "fat_saturated_g": round(float(nutrition["fat_saturated_g"].mean()), 1),
                "fat_poly_g": round(float(nutrition["fat_poly_g"].mean()), 1),
                "fat_mono_g": round(float(nutrition["fat_mono_g"].mean()), 1),
            }
            if total_fat > 0:
                for k in ["fat_saturated_g", "fat_poly_g", "fat_mono_g"]:
                    pct = 100 * nutrition[k].sum() / total_fat
                    nutrition_summary["fat_profile"][f"{k}_pct"] = round(float(pct), 1)

        # Calories by meal and meal pattern (optional)
        if zip_data.nutrition_by_meal is not None and not zip_data.nutrition_by_meal.empty:
            by_meal = zip_data.nutrition_by_meal
            if "meal" in by_meal.columns and "calories" in by_meal.columns:
                calories_by_meal = by_meal.groupby("meal")["calories"].mean().round(1).to_dict()
                nutrition_summary["calories_by_meal"] = {k: float(v) for k, v in calories_by_meal.items()}
                all_dates = set(zip_data.nutrition_daily["date"].dt.date)
                meal_pattern: dict[str, Any] = {}
                for meal in by_meal["meal"].unique():
                    meal_dates = set(by_meal[by_meal["meal"] == meal]["date"].dt.date)
                    days_with = len(meal_dates)
                    days_without = len(all_dates - meal_dates)
                    meal_pattern[str(meal)] = {"days_with": days_with, "days_without": days_without}
                nutrition_summary["meal_pattern"] = meal_pattern

        exercise_summary: dict[str, Any] = {
            "days_logged": int(exercise["date"].nunique()) if not exercise.empty else 0,
        }
        for col in ["exercise_minutes", "exercise_calories", "steps"]:
            if col in exercise.columns and not exercise[col].dropna().empty:
                exercise_summary[f"avg_{col}"] = round(float(exercise[col].mean()), 1)

        if "session_type" in exercise.columns:
            exercise_summary["session_type_counts"] = (
                exercise["session_type"].value_counts(dropna=True).to_dict()
            )

        exercise_history = self._build_exercise_history(exercise)
        exercise_summary["exercise_history"] = exercise_history

        first_weight = float(measures.iloc[0]["weight"])
        last_weight = float(measures.iloc[-1]["weight"])
        total_loss = round(last_weight - first_weight, 2)
        days_span = (measures.iloc[-1]["date"] - measures.iloc[0]["date"]).days
        weeks = max(days_span / 7.0, 0.001)
        loss_rate = round((last_weight - first_weight) / weeks, 2)

        steps_mfp = None
        if not exercise.empty and "steps" in exercise.columns and not exercise["steps"].dropna().empty:
            steps_mfp = int(round(float(exercise["steps"].mean()), 0))

        pdf_report_v2 = build_pdf_report_v2(pdf_metrics)
        weight_withings = (
            pdf_report_v2.get("body", {}).get("latest_weight_kg")
            or pdf_metrics.get("latest_weight_kg")
        )
        steps_withings = (
            pdf_report_v2.get("activity", {}).get("avg_daily_steps")
            or pdf_metrics.get("daily_steps_avg")
        )
        comparison = {
            "weight_mfp_kg": round(last_weight, 2),
            "weight_withings_kg": weight_withings,
            "steps_mfp": steps_mfp,
            "steps_withings": steps_withings,
        }

        # Weekly summary
        weekly_summary = self._build_weekly_summary(measures, nutrition, exercise)

        # Weekly adherence (score per week) with personalized targets
        weekly_adherence = self._build_weekly_adherence(
            measures, nutrition, exercise, targets=adherence_targets
        )

        # Projection until target date
        projection = self._build_projection(measures, target_date)

        # Retention flag
        retention_flag = self._build_retention_flag(measures, nutrition)

        # Alerts (categorized)
        alerts = self._build_alerts(zip_data, nutrition_summary, nutrition)

        # Sleep block: prefer pdf_report_v2.sleep when available, else pdf_metrics
        sleep_block: dict[str, Any] = {}
        v2_sleep = pdf_report_v2.get("sleep", {})
        if v2_sleep.get("total_sleep_time"):
            sleep_block["avg_duration"] = v2_sleep["total_sleep_time"]
        elif pdf_metrics.get("sleep_avg"):
            sleep_block["avg_duration"] = pdf_metrics["sleep_avg"]
        if v2_sleep.get("efficiency_pct") is not None:
            sleep_block["avg_efficiency_pct"] = v2_sleep["efficiency_pct"]
        elif pdf_metrics.get("sleep_efficiency_pct") is not None:
            sleep_block["avg_efficiency_pct"] = pdf_metrics["sleep_efficiency_pct"]

        weight_section: dict[str, Any] = {
            "latest_weight_kg": round(latest_weight, 2),
            "latest_ma5_kg": round(latest_ma5, 2) if latest_ma5 is not None else None,
            "latest_ma7_kg": round(latest_ma7, 2) if latest_ma7 is not None else None,
            "ma7_change_kg": round(float(last_ma7 - first_ma7), 2)
            if first_ma7 is not None and last_ma7 is not None
            else None,
            "total_loss_kg": total_loss,
            "loss_rate_kg_per_week": loss_rate,
            "first_weight_kg": round(first_weight, 2),
            "weight_history": weight_history,
            "last_15_days": last_n_days,
        }
        if body_fat_block:
            weight_section["body_fat"] = body_fat_block
        # PDF trends (more reliable than daily bioimpedance)
        if pdf_metrics.get("fat_mass_trend_kg") is not None:
            weight_section["pdf_fat_mass_trend_kg"] = pdf_metrics["fat_mass_trend_kg"]
        if pdf_metrics.get("lean_mass_trend_kg") is not None:
            weight_section["pdf_lean_mass_trend_kg"] = pdf_metrics["lean_mass_trend_kg"]

        return {
            "meta": {
                "target_date": target_date,
                "user": user_info,
                "adherence_targets": adherence_targets,
            },
            "weight": weight_section,
            "nutrition": nutrition_summary,
            "exercise": exercise_summary,
            "comparison": comparison,
            "pdf_report": pdf_metrics,
            "pdf_report_v2": pdf_report_v2,
            "weekly_summary": weekly_summary,
            "weekly_adherence": weekly_adherence,
            "projection": projection,
            "retention_flag": retention_flag,
            "alerts": alerts,
            "sleep": sleep_block,
        }

    @staticmethod
    def _build_weight_records(df: pd.DataFrame) -> list[dict[str, Any]]:
        """Build list of weight records with no NaN (JSON-safe)."""
        records = []
        for _, row in df.iterrows():
            rec = {
                "date": row["date"].strftime("%Y-%m-%d"),
                "weight": round(float(row["weight"]), 2),
            }
            rec["ma5"] = round(float(row["ma5"]), 2) if pd.notna(row["ma5"]) else None
            rec["ma7"] = round(float(row["ma7"]), 2) if pd.notna(row["ma7"]) else None
            records.append(rec)
        return records

    @staticmethod
    def _build_nutrition_history(df: pd.DataFrame) -> list[dict[str, Any]]:
        """Build list of nutrition records (JSON-safe, no NaN)."""
        records = []
        cols = ["date", "calories", "protein_g", "fiber_g", "sodium_mg"]
        if "carbs_g" in df.columns:
            cols.append("carbs_g")
        if "fat_g" in df.columns:
            cols.append("fat_g")
        for _, row in df.iterrows():
            rec: dict[str, Any] = {
                "date": row["date"].strftime("%Y-%m-%d"),
                "calories": round(float(row["calories"]), 1),
                "protein_g": round(float(row["protein_g"]), 1),
                "fiber_g": round(float(row["fiber_g"]), 1),
                "sodium_mg": round(float(row["sodium_mg"]), 1),
            }
            if "carbs_g" in cols:
                rec["carbs_g"] = round(float(row["carbs_g"]), 1) if pd.notna(row["carbs_g"]) else None
            if "fat_g" in cols:
                rec["fat_g"] = round(float(row["fat_g"]), 1) if pd.notna(row["fat_g"]) else None
            records.append(rec)
        return records

    @staticmethod
    def _build_weekly_summary(
        measures: pd.DataFrame,
        nutrition: pd.DataFrame,
        exercise: pd.DataFrame,
    ) -> list[dict[str, Any]]:
        """Build weekly aggregated summary."""
        if measures.empty:
            return []
        measures = measures.copy()
        measures["week"] = measures["date"].dt.isocalendar().week
        measures["year"] = measures["date"].dt.isocalendar().year
        measures["week_key"] = measures["year"].astype(str) + "-W" + measures["week"].astype(str).str.zfill(2)

        result: list[dict[str, Any]] = []
        for week_key in measures["week_key"].unique():
            week_measures = measures[measures["week_key"] == week_key]
            rec: dict[str, Any] = {
                "week": week_key,
                "avg_weight_kg": round(float(week_measures["weight"].mean()), 2),
                "days": len(week_measures),
            }
            week_dates = set(week_measures["date"].dt.date)
            if not nutrition.empty:
                week_nutrition = nutrition[nutrition["date"].dt.date.isin(week_dates)]
                if not week_nutrition.empty:
                    rec["avg_calories"] = round(float(week_nutrition["calories"].mean()), 1)
            if not exercise.empty:
                week_exercise = exercise[exercise["date"].dt.date.isin(week_dates)]
                if not week_exercise.empty:
                    if "exercise_minutes" in week_exercise.columns:
                        rec["avg_exercise_minutes"] = round(float(week_exercise["exercise_minutes"].mean()), 1)
                    if "steps" in week_exercise.columns and not week_exercise["steps"].dropna().empty:
                        rec["avg_steps"] = round(float(week_exercise["steps"].mean()), 0)
            result.append(rec)
        return sorted(result, key=lambda x: x["week"])

    @staticmethod
    def _build_alerts(
        zip_data: ZipData,
        nutrition_summary: dict[str, Any],
        nutrition: pd.DataFrame,
    ) -> dict[str, list[str]]:
        """Build categorized alerts: critical, warning, info."""
        critical: list[str] = []
        warning: list[str] = []
        info: list[str] = []

        # Critical: extreme sodium (>4000 mg in several days), very low calories repeated, kidney risk
        high_sodium_extreme_days = int((nutrition["sodium_mg"] > 4000).sum())
        if high_sodium_extreme_days >= 3:
            critical.append(f"Sódio extremo (>4000 mg) em {high_sodium_extreme_days} dias")
        days_below_1600 = nutrition_summary.get("days_below_1600", 0)
        cal_low = nutrition_summary.get("calorie_low_threshold", 1600)
        if days_below_1600 >= 5:
            critical.append(f"Calorias muito baixas (<{cal_low}) em {days_below_1600} dias")

        # Warning: recurring low protein, low fiber, high saturated fat, calorie excess
        if nutrition_summary.get("days_protein_170_plus", 0) < nutrition["date"].nunique() * 0.5:
            warning.append("Proteína baixa recorrente")
        if nutrition_summary.get("days_fiber_20_plus", 0) < nutrition["date"].nunique() * 0.5:
            warning.append("Fibra baixa recorrente")
        if "fat_profile" in nutrition_summary:
            fat_sat_pct = nutrition_summary["fat_profile"].get("fat_saturated_g_pct")
            if fat_sat_pct is not None and fat_sat_pct > 10:
                warning.append(f"Gordura saturada acima de 10% em média ({fat_sat_pct:.1f}%)")
        days_above_2200 = nutrition_summary.get("days_above_2200", 0)
        cal_high = nutrition_summary.get("calorie_high_threshold", 2200)
        if days_above_2200 >= 3:
            warning.append(f"Excesso calórico (>{cal_high}) em {days_above_2200} dias")
        if nutrition_summary.get("avg_sodium_mg", 0) > 2300 and high_sodium_extreme_days < 3:
            high_sodium_days = int((nutrition["sodium_mg"] > 2300).sum())
            if high_sodium_days > 0:
                warning.append(f"Sódio alto em {high_sodium_days} dias")

        # Info: days without coffee, steps below average, sugar >50g in few days
        if zip_data.nutrition_by_meal is not None and "meal_pattern" in nutrition_summary:
            for meal, pattern in nutrition_summary["meal_pattern"].items():
                if pattern.get("days_without", 0) > 0 and "Café" in meal:
                    info.append(f"{pattern['days_without']} dias sem {meal}")
        if "days_high_sugar" in nutrition_summary and nutrition_summary["days_high_sugar"] > 0:
            if nutrition_summary["days_high_sugar"] < 3:
                info.append(f"Açúcar acima de 50g em {nutrition_summary['days_high_sugar']} dias")
            else:
                warning.append(f"Açúcar acima de 50g em {nutrition_summary['days_high_sugar']} dias")

        return {"critical": critical, "warning": warning, "info": info}

    @staticmethod
    def _build_weekly_adherence(
        measures: pd.DataFrame,
        nutrition: pd.DataFrame,
        exercise: pd.DataFrame,
        *,
        targets: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Build weekly adherence score with components. Uses targets if provided."""
        if measures.empty:
            return []
        t = targets or ADHERENCE_TARGETS
        cal_lo, cal_hi = t["calorie_range"]
        protein_target = t["protein_g"]
        fiber_target = t["fiber_g"]
        sod_max = t.get("sodium_mg_max", 2500)
        sessions_target = t.get("sessions_per_week", 4)
        measures = measures.copy()
        measures["week"] = measures["date"].dt.isocalendar().week
        measures["year"] = measures["date"].dt.isocalendar().year
        measures["week_key"] = measures["year"].astype(str) + "-W" + measures["week"].astype(str).str.zfill(2)

        result: list[dict[str, Any]] = []
        for week_key in measures["week_key"].unique():
            week_measures = measures[measures["week_key"] == week_key]
            week_dates = set(week_measures["date"].dt.date)
            week_start = week_measures["date"].min()
            week_end = week_measures["date"].max()

            # Daily points for nutrition (calories, protein, fiber, sodium)
            daily_calories: list[float] = []
            daily_protein: list[float] = []
            daily_fiber: list[float] = []
            daily_sodium: list[float] = []

            for d in week_dates:
                day_nutrition = nutrition[nutrition["date"].dt.date == d]
                if day_nutrition.empty:
                    daily_calories.append(0.0)
                    daily_protein.append(0.0)
                    daily_fiber.append(0.0)
                    daily_sodium.append(0.0)
                    continue
                row = day_nutrition.iloc[0]
                cal = float(row["calories"]) if pd.notna(row["calories"]) else 0
                prot = float(row["protein_g"]) if pd.notna(row["protein_g"]) else 0
                fib = float(row["fiber_g"]) if pd.notna(row["fiber_g"]) else 0
                sod = float(row["sodium_mg"]) if pd.notna(row["sodium_mg"]) else 0

                # Calories: 30: in range, 20: ±~5%, 10: ±~10%, 0: outside
                margin_5 = max(50, int((cal_hi - cal_lo) * 0.5))
                margin_10 = max(100, int((cal_hi - cal_lo) * 1.0))
                if cal_lo <= cal <= cal_hi:
                    cal_pts = 30.0
                elif cal_lo - margin_5 <= cal <= cal_hi + margin_5:
                    cal_pts = 20.0
                elif cal_lo - margin_10 <= cal <= cal_hi + margin_10:
                    cal_pts = 10.0
                else:
                    cal_pts = 0.0
                daily_calories.append(cal_pts)

                # Protein: 25: >=target, 20: 90-99%, 10: 80-89%, 0: <80%
                p90 = protein_target * 0.9
                p80 = protein_target * 0.8
                if prot >= protein_target:
                    prot_pts = 25.0
                elif prot >= p90:
                    prot_pts = 20.0
                elif prot >= p80:
                    prot_pts = 10.0
                else:
                    prot_pts = 0.0
                daily_protein.append(prot_pts)

                # Fiber: 15: >=target, 10: target-5 to target-1, 5: target-10 to target-6, 0: <target-10
                fib_10 = max(10, fiber_target - 10)
                fib_5 = max(5, fiber_target - 5)
                if fib >= fiber_target:
                    fib_pts = 15.0
                elif fib >= fib_5:
                    fib_pts = 10.0
                elif fib >= fib_10:
                    fib_pts = 5.0
                else:
                    fib_pts = 0.0
                daily_fiber.append(fib_pts)

                # Sodium: 10: <=sod_max, 7: sod_max+500, 3: sod_max+1500, 0: >sod_max+1500; -2 if >3500 (floor 0)
                if sod <= sod_max:
                    sod_pts = 10.0
                elif sod <= sod_max + 500:
                    sod_pts = 7.0
                elif sod <= sod_max + 1500:
                    sod_pts = 3.0
                else:
                    sod_pts = 0.0
                if sod > 3500:
                    sod_pts = max(0.0, sod_pts - 2.0)
                daily_sodium.append(sod_pts)

            n_days = len(week_dates)
            calories_score = round(sum(daily_calories) / n_days, 1) if n_days else 0.0
            protein_score = round(sum(daily_protein) / n_days, 1) if n_days else 0.0
            fiber_score = round(sum(daily_fiber) / n_days, 1) if n_days else 0.0
            sodium_hydration_score = round(sum(daily_sodium) / n_days, 1) if n_days else 0.0

            # Training: sessions per week (day with exercise_minutes > 0 or exercise_calories > 0)
            sessions = 0
            if not exercise.empty:
                for d in week_dates:
                    day_ex = exercise[exercise["date"].dt.date == d]
                    if not day_ex.empty:
                        ex_row = day_ex.iloc[0]
                        mins = ex_row.get("exercise_minutes") if "exercise_minutes" in ex_row.index else 0
                        cals = ex_row.get("exercise_calories") if "exercise_calories" in ex_row.index else 0
                        if (pd.notna(mins) and float(mins) > 0) or (pd.notna(cals) and float(cals) > 0):
                            sessions += 1
            if sessions >= sessions_target:
                training_score = 20.0
            elif sessions >= sessions_target - 1:
                training_score = 15.0
            elif sessions >= sessions_target - 2:
                training_score = 8.0
            else:
                training_score = 0.0

            # Total score and rating
            total_score = round(sum([calories_score, protein_score, fiber_score, sodium_hydration_score, training_score]), 1)
            if total_score >= 90:
                rating = "excelente"
            elif total_score >= 75:
                rating = "boa"
            elif total_score >= 60:
                rating = "aceitável"
            elif total_score >= 40:
                rating = "fraca"
            else:
                rating = "muito fraca"

            result.append({
                "week_start": week_start.strftime("%Y-%m-%d"),
                "week_end": week_end.strftime("%Y-%m-%d"),
                "score": total_score,
                "rating": rating,
                "components": {
                    "calories_score": calories_score,
                    "protein_score": protein_score,
                    "fiber_score": fiber_score,
                    "sodium_hydration_score": sodium_hydration_score,
                    "training_score": training_score,
                },
                "weekly_targets": {
                    "calorie_range": t["calorie_range"],
                    "protein_g": t["protein_g"],
                    "fiber_g": t["fiber_g"],
                    "sodium_mg_max": t.get("sodium_mg_max", 2500),
                    "sessions_per_week": t.get("sessions_per_week", 4),
                },
            })
        return sorted(result, key=lambda x: x["week_start"])

    @staticmethod
    def _build_projection(measures: pd.DataFrame, target_date: str) -> dict[str, Any]:
        """Build weight projection until target date using fixed scenario rates."""
        if measures.empty or "ma7" not in measures.columns:
            return {}
        ma7_vals = measures["ma7"].dropna()
        if len(ma7_vals) < 2:
            return {}

        current_ma7 = float(ma7_vals.iloc[-1])
        current_weight = float(measures.iloc[-1]["weight"])
        last_date = measures["date"].iloc[-1]
        target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
        if hasattr(last_date, "date"):
            last_date = last_date.date()
        days_until = (target_dt - last_date).days
        if days_until <= 0:
            return {}

        weeks_to_target = round(days_until / 7.0, 1)

        def projected_ma7(rate: float) -> float:
            return round(current_ma7 + rate * weeks_to_target, 2)

        def clamp_rate(r: float) -> float:
            return round(max(-1.2, min(1.0, r)), 2)

        if len(ma7_vals) < MIN_MA7_ROWS_FOR_TREND:
            rates = PROJECTION_FALLBACK_RATES_KG_PER_WEEK
            method = "scenario_rates"
            assumptions = {"scenario_rates_kg_per_week": {k: round(v, 2) for k, v in rates.items()}}
        else:
            ma7_last = float(ma7_vals.iloc[-1])
            ma7_7d_ago = float(ma7_vals.iloc[-8])
            ma7_14d_ago = float(ma7_vals.iloc[-15])
            prev_week_rate = ma7_7d_ago - ma7_14d_ago
            current_week_rate = ma7_last - ma7_7d_ago
            avg_rate = (prev_week_rate + current_week_rate) / 2
            sorted_rates = sorted([prev_week_rate, current_week_rate, avg_rate])
            rates = {
                "optimistic": clamp_rate(sorted_rates[0]),
                "realistic": clamp_rate(sorted_rates[1]),
                "pessimistic": clamp_rate(sorted_rates[2]),
            }
            method = "trend_from_prev_and_current_week"
            assumptions = {
                "prev_week_rate": round(prev_week_rate, 2),
                "current_week_rate": round(current_week_rate, 2),
                "avg_rate": round(avg_rate, 2),
                "scenario_rates_kg_per_week": dict(rates),
            }

        scenarios = {}
        for name, rate in rates.items():
            scenarios[name] = {
                "rate_kg_per_week": rate,
                "projected_ma7_kg": projected_ma7(rate),
            }

        slowest = abs(rates["pessimistic"])
        fastest = abs(rates["optimistic"])
        note = f"Baseado em cenários de perda entre {slowest:.2f} e {fastest:.2f} kg/sem."
        if rates["optimistic"] > 0 or rates["pessimistic"] > 0:
            note = f"Baseado em cenários entre {rates['optimistic']:.2f} e {rates['pessimistic']:.2f} kg/sem."

        return {
            "target_date": target_date,
            "method": method,
            "current_ma7_kg": round(current_ma7, 2),
            "current_weight_kg": round(current_weight, 2),
            "weeks_to_target": weeks_to_target,
            "assumptions": assumptions,
            "scenarios": scenarios,
            "note": note,
        }

    @staticmethod
    def _build_retention_flag(measures: pd.DataFrame, nutrition: pd.DataFrame) -> dict[str, Any]:
        """Build retention flag: probable retention if weight up short-term, MA7 stable, and triggers."""
        if measures.empty or len(measures) < 4:
            return {"is_probable_retention": False, "confidence": "low", "reason_codes": [], "metrics": {}}
        last_row = measures.iloc[-1]
        row_3d_ago = measures.iloc[-4]
        weight_now = float(last_row["weight"])
        weight_3d = float(row_3d_ago["weight"])
        ma7_now = float(last_row["ma7"]) if pd.notna(last_row["ma7"]) else None
        ma7_3d = float(row_3d_ago["ma7"]) if pd.notna(row_3d_ago["ma7"]) else None

        weight_change_3d = round(weight_now - weight_3d, 2)
        ma7_change_3d = round(ma7_now - ma7_3d, 2) if (ma7_now is not None and ma7_3d is not None) else None

        # Condition 1: weight_now - weight_3d >= 0.6
        cond1 = weight_change_3d >= 0.6
        # Condition 2: MA7_now <= MA7_3d + 0.1
        cond2 = (ma7_now is not None and ma7_3d is not None and ma7_now <= ma7_3d + 0.1)

        # Triggers in last 4 days: calories out of range, sodium > 3500, fiber < 15
        last_4_dates = measures["date"].tail(4).dt.date.tolist()
        high_sodium_days = 0
        high_calorie_days = 0
        low_fiber_days = 0
        calories_out_days = 0
        if not nutrition.empty:
            for d in last_4_dates:
                day_nut = nutrition[nutrition["date"].dt.date == d]
                if not day_nut.empty:
                    row = day_nut.iloc[0]
                    cal = float(row["calories"]) if pd.notna(row["calories"]) else 0
                    sod = float(row["sodium_mg"]) if pd.notna(row["sodium_mg"]) else 0
                    fib = float(row["fiber_g"]) if pd.notna(row["fiber_g"]) else 0
                    if sod > 3500:
                        high_sodium_days += 1
                    if cal > 2200 or cal < 1600:
                        calories_out_days += 1
                    if cal > 2200:
                        high_calorie_days += 1
                    if fib < 15:
                        low_fiber_days += 1
        has_trigger = high_sodium_days > 0 or calories_out_days > 0 or low_fiber_days > 0

        is_probable = cond1 and cond2 and has_trigger
        reason_codes: list[str] = []
        if weight_change_3d >= 0.6:
            reason_codes.append("weight_up_short_term")
        if cond2:
            reason_codes.append("ma7_stable_or_down")
        if high_sodium_days > 0:
            reason_codes.append("recent_high_sodium")
        if calories_out_days > 0:
            reason_codes.append("recent_calories_out_of_range")
        if low_fiber_days > 0:
            reason_codes.append("recent_low_fiber")

        confidence = "moderate" if is_probable else "low"
        ma5_change = None
        if "ma5" in measures.columns and len(measures) >= 4:
            ma5_now = float(measures.iloc[-1]["ma5"]) if pd.notna(measures.iloc[-1]["ma5"]) else None
            ma5_3d = float(measures.iloc[-4]["ma5"]) if pd.notna(measures.iloc[-4]["ma5"]) else None
            if ma5_now is not None and ma5_3d is not None:
                ma5_change = round(ma5_now - ma5_3d, 2)

        return {
            "is_probable_retention": is_probable,
            "confidence": confidence,
            "reason_codes": reason_codes,
            "metrics": {
                "weight_change_3d_kg": weight_change_3d,
                "ma5_change_3d_kg": ma5_change,
                "ma7_change_3d_kg": ma7_change_3d,
                "high_sodium_days_last_4d": high_sodium_days,
                "high_calorie_days_last_4d": high_calorie_days,
            },
        }

    @staticmethod
    def _build_exercise_history(df: pd.DataFrame) -> list[dict[str, Any]]:
        """Build list of exercise records (JSON-safe, no NaN)."""
        records = []
        cols = [c for c in ["exercise_minutes", "steps", "exercise_calories"] if c in df.columns]
        for _, row in df.iterrows():
            rec: dict[str, Any] = {"date": row["date"].strftime("%Y-%m-%d")}
            for col in cols:
                val = row[col]
                rec[col] = round(float(val), 1) if pd.notna(val) else None
            for col in ["exercise_minutes", "steps", "exercise_calories"]:
                if col not in rec:
                    rec[col] = None
            records.append(rec)
        return records
