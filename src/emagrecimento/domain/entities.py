"""Domain entities - pure data structures with no external dependencies."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=False)
class ZipData:
    """Extracted data from MyFitnessPal ZIP export."""

    measures: pd.DataFrame
    nutrition_daily: pd.DataFrame
    exercise_daily: pd.DataFrame
    nutrition_by_meal: pd.DataFrame | None = None
