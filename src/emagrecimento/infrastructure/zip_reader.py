"""ZIP reader adapter - extracts data from MyFitnessPal export."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import BinaryIO, Union

import pandas as pd

from emagrecimento.application.interfaces import IZipReader
from emagrecimento.domain.entities import ZipData
from emagrecimento.domain.value_objects import find_column, find_column_optional, normalize_text, parse_duration_minutes


class ZipFileZipReader(IZipReader):
    """Extract ZipData from MyFitnessPal ZIP using zipfile + pandas."""

    def extract(self, source: Union[str, Path, BinaryIO]) -> ZipData:
        with zipfile.ZipFile(source) as zf:
            names = zf.namelist()

            measures_name = next((n for n in names if "medidas" in normalize_text(n)), None)
            nutrition_name = next((n for n in names if "alimentacao" in normalize_text(n)), None)
            exercise_name = next((n for n in names if "exercicios" in normalize_text(n)), None)

            if not measures_name or not nutrition_name or not exercise_name:
                raise FileNotFoundError(
                    "Não encontrei todos os CSVs esperados dentro do ZIP. "
                    f"Arquivos encontrados: {names}"
                )

            measures = self._read_csv_from_zip(zf, measures_name)
            nutrition = self._read_csv_from_zip(zf, nutrition_name)
            exercise = self._read_csv_from_zip(zf, exercise_name)

        measures = self._process_measures(measures)
        nutrition_daily, nutrition_by_meal = self._process_nutrition(nutrition)
        exercise_daily = self._process_exercise(exercise)

        return ZipData(
            measures=measures,
            nutrition_daily=nutrition_daily,
            exercise_daily=exercise_daily,
            nutrition_by_meal=nutrition_by_meal,
        )

    @staticmethod
    def _read_csv_from_zip(zf: zipfile.ZipFile, name: str) -> pd.DataFrame:
        with zf.open(name) as f:
            raw = f.read()
        return pd.read_csv(io.BytesIO(raw))

    @staticmethod
    def _process_measures(df: pd.DataFrame) -> pd.DataFrame:
        date_col = find_column(list(df.columns), ["Data", "Date"])
        weight_col = find_column(list(df.columns), ["Peso", "Weight"])
        body_fat_col = find_column_optional(list(df.columns), ["Body Fat %", "Body Fat", "Gordura corporal"])

        cols = [date_col, weight_col]
        if body_fat_col:
            cols.append(body_fat_col)

        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df[weight_col] = pd.to_numeric(df[weight_col], errors="coerce")
        if body_fat_col:
            df[body_fat_col] = pd.to_numeric(df[body_fat_col], errors="coerce")

        df = df[cols].rename(columns={date_col: "date", weight_col: "weight"})
        if body_fat_col:
            df = df.rename(columns={body_fat_col: "body_fat_pct"})
        df = df.dropna(subset=["date", "weight"]).sort_values("date").reset_index(drop=True)
        df["ma5"] = df["weight"].rolling(5).mean()
        df["ma7"] = df["weight"].rolling(7).mean()
        return df

    @staticmethod
    def _process_nutrition(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame | None]:
        nutrition_date_col = find_column(list(df.columns), ["Data", "Date"])
        required_candidates = {
            "calories": ["Calorias", "Calories"],
            "protein_g": ["Proteínas (g)", "Proteinas (g)", "Protein (g)"],
            "carbs_g": ["Carboidratos (g)", "Carbohydrates (g)"],
            "fat_g": ["Gorduras (g)", "Fat (g)"],
            "fiber_g": ["Fibra", "Fiber"],
            "sodium_mg": ["Sódio (mg)", "Sodio (mg)", "Sodium (mg)"],
        }
        optional_candidates = {
            "sugar_g": ["Açucar", "Açúcar", "Sugar"],
            "fat_saturated_g": ["Gorduras saturadas", "Saturated fat"],
            "fat_poly_g": ["Gorduras poliinsaturadas", "Polyunsaturated fat"],
            "fat_mono_g": ["Gorduras monoinsaturadas", "Monounsaturated fat"],
            "fat_trans_g": ["Gorduras trans", "Trans fat"],
        }
        meal_col = find_column_optional(list(df.columns), ["Refeição", "Meal"])

        selected_cols: dict[str, str] = {"date": nutrition_date_col}
        for key, candidates in required_candidates.items():
            selected_cols[key] = find_column(list(df.columns), candidates)
        for key, candidates in optional_candidates.items():
            col = find_column_optional(list(df.columns), candidates)
            if col:
                selected_cols[key] = col

        cols_to_use = [selected_cols["date"], *[selected_cols[k] for k in required_candidates]]
        if meal_col:
            selected_cols["meal"] = meal_col
            cols_to_use.append(meal_col)
        for k in optional_candidates:
            if k in selected_cols:
                cols_to_use.append(selected_cols[k])

        df = df[cols_to_use].copy()
        df = df.rename(columns={v: k for k, v in selected_cols.items()})
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for col in [c for c in df.columns if c not in ("date", "meal")]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        nutrition_daily = df.groupby("date", as_index=False).sum(numeric_only=True).sort_values("date")

        nutrition_by_meal: pd.DataFrame | None = None
        if "meal" in df.columns:
            meal_df = df.dropna(subset=["meal"])
            meal_df = meal_df[meal_df["meal"].astype(str).str.strip() != ""]
            if not meal_df.empty:
                nutrition_by_meal = meal_df.sort_values(["date", "meal"]).reset_index(drop=True)

        return nutrition_daily, nutrition_by_meal

    @staticmethod
    def _process_exercise(df: pd.DataFrame) -> pd.DataFrame:
        exercise_date_col = find_column(list(df.columns), ["Data", "Date"])
        exercise_map = {"date": exercise_date_col}
        maybe_cols = {
            "exercise_calories": ["Calorias de exercícios", "Calorias de exercicios", "Exercise Calories"],
            "exercise_minutes": ["Minutos de exercício", "Minutos de exercicio", "Exercise Minutes"],
            "steps": ["Passos", "Steps"],
            "exercise_name": ["Exercício", "Exercicio", "Exercise"],
            "exercise_type": ["Tipo", "Type"],
        }

        for key, candidates in maybe_cols.items():
            try:
                exercise_map[key] = find_column(list(df.columns), candidates)
            except KeyError:
                pass

        # Avoid exercise_name matching "Minutos de exercício" (partial match conflict)
        if "exercise_minutes" in exercise_map and "exercise_name" in exercise_map:
            if exercise_map["exercise_name"] == exercise_map["exercise_minutes"]:
                del exercise_map["exercise_name"]
        if "exercise_minutes" in exercise_map and "exercise_type" in exercise_map:
            if exercise_map["exercise_type"] == exercise_map["exercise_minutes"]:
                del exercise_map["exercise_type"]

        # Use unique columns only to avoid duplicate column names
        seen_cols: set[str] = set()
        cols_to_use: list[str] = []
        for k in exercise_map:
            col = exercise_map[k]
            if col not in seen_cols:
                seen_cols.add(col)
                cols_to_use.append(col)

        df = df[cols_to_use].copy()
        df = df.rename(columns={v: k for k, v in exercise_map.items()})
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

        # exercise_minutes: parse duration (1:30, 45 min) and sanity check; values > 600 treated as seconds
        if "exercise_minutes" in df.columns:
            df["exercise_minutes"] = df["exercise_minutes"].apply(parse_duration_minutes)

        # exercise_calories: cap 2000 per row (single session max)
        if "exercise_calories" in df.columns:
            df["exercise_calories"] = pd.to_numeric(df["exercise_calories"], errors="coerce")
            df["exercise_calories"] = df["exercise_calories"].clip(upper=2000)

        if "steps" in df.columns:
            df["steps"] = pd.to_numeric(df["steps"], errors="coerce")
            df["steps"] = df["steps"].clip(lower=0, upper=100000)

        # Deduplicate: same workout (date+exercise_name) logged multiple times -> take max per group
        if "exercise_name" in df.columns:
            col = df["exercise_name"]
            if isinstance(col, pd.DataFrame):
                col = col.iloc[:, 0]
            df["exercise_name"] = col.fillna("").astype(str).str.strip()
            dedup_cols = [c for c in ["exercise_calories", "exercise_minutes", "steps"] if c in df.columns]
            if dedup_cols:
                df = (
                    df.groupby(["date", "exercise_name"], as_index=False)[dedup_cols]
                    .max()
                    .reset_index(drop=True)
                )

        numeric_cols = [c for c in ["exercise_calories", "exercise_minutes", "steps"] if c in df.columns]
        result = df.groupby("date", as_index=False)[numeric_cols].sum().sort_values("date")

        # Cap daily totals (sanity: max 10h exercise, 3000 cal)
        if "exercise_minutes" in result.columns:
            result["exercise_minutes"] = result["exercise_minutes"].clip(upper=600)
        if "exercise_calories" in result.columns:
            result["exercise_calories"] = result["exercise_calories"].clip(upper=3000)

        if "exercise_name" in df.columns:
            workout_days = (
                df.dropna(subset=["exercise_name"])
                .assign(is_treadmill=lambda d: d["exercise_name"].astype(str).str.contains("esteira", case=False, na=False))
                .groupby("date", as_index=False)["is_treadmill"]
                .max()
            )
            workout_days["session_type"] = workout_days["is_treadmill"].map({True: "treadmill", False: "other"})
            result = result.merge(workout_days[["date", "session_type"]], on="date", how="left")

        return result
