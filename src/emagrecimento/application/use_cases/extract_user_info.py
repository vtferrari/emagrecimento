"""Extract user info from ZIP and PDF data for form pre-fill."""

from __future__ import annotations

import math
from typing import Any

from emagrecimento.domain.entities import ZipData


class ExtractUserInfoFromFiles:
    """
    Extract user info (weight, height, age, sex) from ZIP and PDF data.
    Used to auto-fill form when user does not provide these values.
    - Weight: from measures (last row) or PDF latest_weight_kg
    - Height: derived from PDF BMI + weight (height_cm = 100 * sqrt(weight/bmi))
    - Age: from PDF "30yo" pattern
    - Sex: from PDF "Biological Sex: Female/Male"
    """

    def execute(
        self,
        zip_data: ZipData | None,
        pdf_metrics: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Extract user info dict with weight_kg, height_cm, age, sex (as available)."""
        result: dict[str, Any] = {}
        weight_kg = None

        if pdf_metrics and pdf_metrics.get("latest_weight_kg") is not None:
            weight_kg = float(pdf_metrics["latest_weight_kg"])
        if weight_kg is None and zip_data and not zip_data.measures.empty:
            last = zip_data.measures.iloc[-1]
            w = last.get("weight")
            if w is not None and not math.isnan(w):
                weight_kg = float(w)
        if weight_kg is not None:
            result["weight_kg"] = round(weight_kg, 1)

        # Derive height from BMI when we have both weight and bmi
        bmi = pdf_metrics.get("bmi_avg") if pdf_metrics else None
        if bmi is not None and weight_kg is not None and float(bmi) > 0:
            try:
                height_cm = 100 * math.sqrt(float(weight_kg) / float(bmi))
                if 100 <= height_cm <= 250:
                    result["height_cm"] = int(round(height_cm))
            except (ValueError, TypeError):
                pass

        if pdf_metrics:
            if pdf_metrics.get("age_years") is not None:
                result["age"] = int(pdf_metrics["age_years"])
            if pdf_metrics.get("biological_sex") is not None:
                result["sex"] = pdf_metrics["biological_sex"]

        return result
