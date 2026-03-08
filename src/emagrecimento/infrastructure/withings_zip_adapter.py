"""Withings ZIP adapter - loads health data from Withings export ZIP."""

from __future__ import annotations

import io
import logging
import zipfile

import pandas as pd

from emagrecimento.application.interfaces import WithingsZipRepository
from emagrecimento.domain.withings_zip import (
    WithingsActivityDay,
    WithingsBodySnapshot,
    WithingsEcgReading,
    WithingsHealthRecord,
    WithingsSleepNight,
)

logger = logging.getLogger(__name__)

MEASURE_TYPE_MAP = {
    "Weight": "weight_kg",
    "Fat Mass Weight": "fat_mass_kg",
    "Muscle Mass": "muscle_mass_kg",
    "Bone mass": "bone_mass_kg",
    "Water mass": "water_pct",
    "Visceral Fat": "visceral_fat",
    "Basal Metabolic Rate (BMR)": "bmr_kcal",
    "Metabolic Age": "metabolic_age",
    "Fat Free Mass": "fat_free_mass_kg",
}


def _to_native(val: object) -> object:
    """Convert pandas/numpy types to Python native for JSON safety."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    return val


def _safe_float(val: object) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _safe_int(val: object) -> int | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


class WithingsZipAdapter(WithingsZipRepository):
    """Load WithingsHealthRecord from Withings export ZIP bytes."""

    def load(self, zip_bytes: bytes | None) -> WithingsHealthRecord | None:
        """Load WithingsHealthRecord from ZIP bytes. Returns None if invalid."""
        if not zip_bytes or len(zip_bytes) == 0:
            return None
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
                names = zf.namelist()
                measures_name = next((n for n in names if n.startswith("Measures |") and n.endswith(".csv")), None)
                sleep_name = next((n for n in names if n.startswith("Sleep |") and n.endswith(".csv")), None)
                steps_name = next((n for n in names if n.startswith("Steps |") and n.endswith(".csv")), None)
                signals_prefix = "Signals |"

                body_snapshots: list[WithingsBodySnapshot] = []
                sleep_nights: list[WithingsSleepNight] = []
                activity_days: list[WithingsActivityDay] = []
                ecg_readings: list[WithingsEcgReading] = []

                if measures_name:
                    body_snapshots = self._parse_measures(zf, measures_name)
                else:
                    logger.info("Withings ZIP: no Measures CSV found")

                if sleep_name:
                    sleep_nights = self._parse_sleep(zf, sleep_name)
                else:
                    logger.info("Withings ZIP: no Sleep CSV found")

                if steps_name:
                    activity_days = self._parse_steps(zf, steps_name)
                else:
                    logger.info("Withings ZIP: no Steps CSV found")

                ecg_files = [n for n in names if n.startswith(signals_prefix) and "ECG" in n and n.endswith(".csv")]
                for ecg_path in ecg_files:
                    readings = self._parse_ecg(zf, ecg_path)
                    ecg_readings.extend(readings)

                if not body_snapshots and not sleep_nights and not activity_days and not ecg_readings:
                    return None

                return WithingsHealthRecord(
                    body_snapshots=tuple(body_snapshots),
                    sleep_nights=tuple(sleep_nights),
                    activity_days=tuple(activity_days),
                    ecg_readings=tuple(ecg_readings),
                )
        except (zipfile.BadZipFile, KeyError, ValueError) as e:
            logger.warning("Withings ZIP load failed: %s", e)
            return None

    def _read_csv(self, zf: zipfile.ZipFile, name: str) -> pd.DataFrame:
        with zf.open(name) as f:
            raw = f.read()
        return pd.read_csv(io.BytesIO(raw), na_values=["-"])

    def _parse_measures(self, zf: zipfile.ZipFile, name: str) -> list[WithingsBodySnapshot]:
        df = self._read_csv(zf, name)
        cols = {c.strip(): c for c in df.columns}
        date_col = cols.get("Date") or cols.get("date")
        value_col = cols.get("Value") or cols.get("value")
        type_col = cols.get("Measure type") or next((c for c in df.columns if "measure" in str(c).lower() and "type" in str(c).lower()), None)
        if not all([date_col, value_col, type_col]):
            return []

        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col])
        df["_date_str"] = df[date_col].dt.strftime("%Y-%m-%d")
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")

        result: dict[str, dict[str, object]] = {}
        for _, row in df.iterrows():
            date_str = row["_date_str"]
            mtype = str(row[type_col]).strip()
            key = MEASURE_TYPE_MAP.get(mtype)
            if not key:
                continue
            val = row[value_col]
            if pd.isna(val):
                continue
            if date_str not in result:
                result[date_str] = {}
            result[date_str][key] = val

        snapshots: list[WithingsBodySnapshot] = []
        for date_str in sorted(result.keys()):
            r = result[date_str]
            weight = _safe_float(r.get("weight_kg"))
            if weight is None:
                continue
            fat = _safe_float(r.get("fat_mass_kg")) or 0.0
            muscle = _safe_float(r.get("muscle_mass_kg")) or 0.0
            visceral = _safe_float(r.get("visceral_fat")) or 0.0
            meta_age = _safe_int(r.get("metabolic_age")) or 0
            snapshots.append(
                WithingsBodySnapshot(
                    date=date_str,
                    weight_kg=round(weight, 2),
                    fat_mass_kg=round(fat, 2),
                    muscle_mass_kg=round(muscle, 2),
                    visceral_fat=round(visceral, 2),
                    metabolic_age=meta_age,
                    bone_mass_kg=_safe_float(r.get("bone_mass_kg")),
                    water_pct=_safe_float(r.get("water_pct")),
                    bmr_kcal=_safe_int(r.get("bmr_kcal")),
                    fat_free_mass_kg=_safe_float(r.get("fat_free_mass_kg")),
                )
            )
        return snapshots

    def _parse_sleep(self, zf: zipfile.ZipFile, name: str) -> list[WithingsSleepNight]:
        df = self._read_csv(zf, name)
        cols = {c.strip(): c for c in df.columns}
        date_col = cols.get("Date") or cols.get("date")
        light_col = cols.get("Light duration") or "Light duration"
        deep_col = cols.get("Deep duration") or "Deep duration"
        rem_col = cols.get("REM duration") or "REM duration"
        awake_col = cols.get("Awake duration") or "Awake duration"
        min_hr = cols.get("Min HR") or "Min HR"
        max_hr = cols.get("Max HR") or "Max HR"
        avg_hr = cols.get("HR average") or "HR average"

        if date_col not in df.columns:
            return []

        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col])
        for c in [light_col, deep_col, rem_col, awake_col]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        for c in [min_hr, max_hr, avg_hr]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        result: list[WithingsSleepNight] = []
        for _, row in df.iterrows():
            date_str = row[date_col].strftime("%Y-%m-%d")
            light_s = float(row.get(light_col, 0) or 0)
            deep_s = float(row.get(deep_col, 0) or 0)
            rem_s = float(row.get(rem_col, 0) or 0)
            awake_s = float(row.get(awake_col, 0) or 0)
            total_s = light_s + deep_s + rem_s + awake_s
            if total_s <= 0:
                continue
            result.append(
                WithingsSleepNight(
                    date=date_str,
                    total_h=round(total_s / 3600, 2),
                    light_h=round(light_s / 3600, 2),
                    deep_h=round(deep_s / 3600, 2),
                    rem_h=round(rem_s / 3600, 2),
                    awake_h=round(awake_s / 3600, 2),
                    hr_min=int(row.get(min_hr, 0) or 0),
                    hr_max=int(row.get(max_hr, 0) or 0),
                    hr_avg=int(row.get(avg_hr, 0) or 0),
                )
            )
        return result

    def _parse_steps(self, zf: zipfile.ZipFile, name: str) -> list[WithingsActivityDay]:
        df = self._read_csv(zf, name)
        cols = {c.strip(): c for c in df.columns}
        date_col = cols.get("Date") or cols.get("date")
        value_col = cols.get("Value") or cols.get("value")
        if date_col not in df.columns or value_col not in df.columns:
            return []

        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
        df = df.dropna(subset=[date_col, value_col])
        grouped = df.groupby(date_col)[value_col].sum().reset_index()
        result: list[WithingsActivityDay] = []
        for _, row in grouped.iterrows():
            steps_val = int(row[value_col])
            if steps_val > 100_000:
                continue
            date_str = row[date_col].strftime("%Y-%m-%d")
            result.append(WithingsActivityDay(date=date_str, steps=steps_val))
        return result

    def _parse_ecg(self, zf: zipfile.ZipFile, name: str) -> list[WithingsEcgReading]:
        df = self._read_csv(zf, name)
        cols = {c.strip().lower(): c for c in df.columns}
        date_col = cols.get("date") or cols.get("Date")
        hr_col = cols.get("hr") or cols.get("HR")
        value_col = cols.get("value") or cols.get("Value")
        if not all([date_col, hr_col, value_col]):
            return []

        result: list[WithingsEcgReading] = []
        for _, row in df.iterrows():
            date_val = row[date_col]
            if pd.isna(date_val):
                continue
            try:
                date_str = pd.to_datetime(date_val).strftime("%Y-%m-%d")
            except Exception:
                continue
            hr = _safe_int(row.get(hr_col))
            value = _safe_int(row.get(value_col))
            if hr is None or value is None:
                continue
            result.append(WithingsEcgReading(date=date_str, hr=hr, value=value))
        return result
