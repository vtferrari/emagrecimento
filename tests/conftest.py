"""Pytest fixtures and configuration."""

import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from emagrecimento.domain.entities import ZipData


@pytest.fixture
def sample_measures_df() -> pd.DataFrame:
    """Sample measures DataFrame for testing (7+ rows for MA7)."""
    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2026-02-01", "2026-02-02", "2026-02-03", "2026-02-04",
            "2026-02-05", "2026-02-06", "2026-02-07", "2026-02-08",
        ]),
        "weight": [85.0, 84.8, 84.5, 84.3, 84.0, 83.8, 83.5, 83.3],
    })
    df["ma5"] = df["weight"].rolling(5).mean()
    df["ma7"] = df["weight"].rolling(7).mean()
    return df


@pytest.fixture
def sample_nutrition_df() -> pd.DataFrame:
    """Sample nutrition DataFrame for testing."""
    return pd.DataFrame({
        "date": pd.to_datetime(["2026-02-01", "2026-02-02"]),
        "calories": [1900, 1850],
        "protein_g": [180, 175],
        "carbs_g": [200, 190],
        "fat_g": [60, 55],
        "fiber_g": [25, 22],
        "sodium_mg": [2000, 1900],
    })


@pytest.fixture
def sample_exercise_df() -> pd.DataFrame:
    """Sample exercise DataFrame for testing."""
    return pd.DataFrame({
        "date": pd.to_datetime(["2026-02-01", "2026-02-02"]),
        "exercise_minutes": [45, 30],
        "exercise_calories": [350, 0],
        "steps": [8000, 5000],
        "session_type": ["treadmill", "other"],
    })


@pytest.fixture
def sample_zip_data(sample_measures_df, sample_nutrition_df, sample_exercise_df) -> ZipData:
    """Sample ZipData for testing."""
    return ZipData(
        measures=sample_measures_df,
        nutrition_daily=sample_nutrition_df,
        exercise_daily=sample_exercise_df,
    )


@pytest.fixture
def measures_15_days_downward() -> pd.DataFrame:
    """21 days with weight trending down (~0.2 kg/week) for trend-based projection tests."""
    dates = pd.date_range("2026-02-01", periods=21, freq="D")
    # ~0.2 kg/week loss: 85 -> ~83.4 over 21 days
    weights = [85.0 - i * 0.08 for i in range(21)]
    df = pd.DataFrame({"date": dates, "weight": weights})
    df["ma5"] = df["weight"].rolling(5).mean()
    df["ma7"] = df["weight"].rolling(7).mean()
    return df


@pytest.fixture
def measures_15_days_upward() -> pd.DataFrame:
    """21 days with weight trending up (~0.2 kg/week) for weight-gain projection tests."""
    dates = pd.date_range("2026-02-01", periods=21, freq="D")
    weights = [83.0 + i * 0.08 for i in range(21)]
    df = pd.DataFrame({"date": dates, "weight": weights})
    df["ma5"] = df["weight"].rolling(5).mean()
    df["ma7"] = df["weight"].rolling(7).mean()
    return df


@pytest.fixture
def zip_data_15_days(
    measures_15_days_downward, sample_nutrition_df, sample_exercise_df
) -> ZipData:
    """ZipData with 21 measures (15+ MA7 values) for trend projection tests."""
    return ZipData(
        measures=measures_15_days_downward,
        nutrition_daily=sample_nutrition_df,
        exercise_daily=sample_exercise_df,
    )


@pytest.fixture
def zip_data_15_days_upward(
    measures_15_days_upward, sample_nutrition_df, sample_exercise_df
) -> ZipData:
    """ZipData with 21 measures trending up for weight-gain projection tests."""
    return ZipData(
        measures=measures_15_days_upward,
        nutrition_daily=sample_nutrition_df,
        exercise_daily=sample_exercise_df,
    )


@pytest.fixture
def sample_zip_data_with_extras() -> ZipData:
    """ZipData with body_fat, nutrition_by_meal, sugar, fat_profile for new analyses."""
    measures = pd.DataFrame({
        "date": pd.to_datetime(["2026-02-01", "2026-02-02", "2026-02-03"]),
        "weight": [85.0, 84.5, 84.0],
        "ma5": [85.0, 84.75, 84.5],
        "ma7": [85.0, 84.75, 84.5],
        "body_fat_pct": [22.5, 22.0, 21.8],
    })
    nutrition = pd.DataFrame({
        "date": pd.to_datetime(["2026-02-01", "2026-02-02"]),
        "calories": [1900, 1850],
        "protein_g": [180, 175],
        "carbs_g": [200, 190],
        "fat_g": [60, 55],
        "fiber_g": [25, 22],
        "sodium_mg": [2000, 2500],
        "sugar_g": [45.0, 55.0],
        "fat_saturated_g": [15.0, 12.0],
        "fat_poly_g": [8.0, 7.0],
        "fat_mono_g": [10.0, 9.0],
    })
    nutrition_by_meal = pd.DataFrame({
        "date": pd.to_datetime(["2026-02-01", "2026-02-01", "2026-02-02"]),
        "meal": ["Café da manhã", "Almoço", "Almoço"],
        "calories": [400, 800, 900],
    })
    exercise = pd.DataFrame({
        "date": pd.to_datetime(["2026-02-01", "2026-02-02"]),
        "exercise_minutes": [45, 30],
        "exercise_calories": [350, 200],
        "steps": [8000, 5000],
        "session_type": ["treadmill", "other"],
    })
    return ZipData(
        measures=measures,
        nutrition_daily=nutrition,
        exercise_daily=exercise,
        nutrition_by_meal=nutrition_by_meal,
    )


@pytest.fixture
def sample_pdf_text() -> str:
    """Sample Withings PDF text for testing (comma as thousands in numbers)."""
    return """
    Overview · 1 Feb-6 Mar 2026
    Weight 84.5 kg Latest -0.3 kg Trend
    BMR 1,850 kcal Latest
    Fat Mass 15.2 kg Latest -0.5 kg Trend
    Muscle Mass 38.5 kg Latest
    Daily Steps 8,500 steps Average
    Sleep Duration 7h30 Average
    Sleep Efficiency 85 % Average
    """
