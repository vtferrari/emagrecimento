"""Domain value objects and pure functions."""

from __future__ import annotations

import re
import unicodedata

import pandas as pd


def normalize_text(value: str) -> str:
    """Normalize text for column matching (NFKD, lowercase, collapse whitespace)."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"\s+", " ", value)
    return value


def find_column(columns: list[str], candidates: list[str]) -> str:
    """Find first matching column by normalized name."""
    normalized_map = {normalize_text(col): col for col in columns}
    for candidate in candidates:
        key = normalize_text(candidate)
        if key in normalized_map:
            return normalized_map[key]
    for col in columns:
        ncol = normalize_text(col)
        for candidate in candidates:
            if normalize_text(candidate) in ncol:
                return col
    raise KeyError(f"Nenhuma coluna encontrada para candidatos: {candidates}. Colunas disponíveis: {columns}")


def find_column_optional(columns: list[str], candidates: list[str]) -> str | None:
    """Find first matching column by normalized name. Returns None if not found."""
    try:
        return find_column(columns, candidates)
    except KeyError:
        return None


def parse_number(value: str | float | int | None) -> float | None:
    """Parse string/number to float, handling locale formats. Returns None for invalid/NaN."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return None
        return float(value)

    text = str(value).strip()
    if not text:
        return None
    text = text.replace("\xa0", " ")
    text = re.sub(r"[^0-9,.+\-]", "", text)
    if text.count(",") == 1 and text.count(".") > 1:
        text = text.replace(".", "")
        text = text.replace(",", ".")
    elif text.count(",") == 1 and text.count(".") == 0:
        before, after = text.split(",", 1)
        # European: 1,850 = 1850 (thousands) vs 84,5 = 84.5 (decimal)
        if len(after) == 3 and after.isdigit():
            text = before + after  # thousands
        else:
            text = before + "." + after  # decimal
    try:
        return float(text)
    except ValueError:
        return None


def parse_duration_minutes(value: str | float | int | None) -> float | None:
    """
    Parse duration string to minutes. Handles:
    - Plain number: "45" -> 45
    - H:MM or HH:MM:SS: "1:30" -> 90, "2:15:00" -> 135
    - "45 min", "1h 30min", "1h30" -> minutes
    - If value > 600, assume seconds: 26621 -> 443 (26621/60)
    Returns None for invalid. Max 600 min (10h) per session.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return None
        val = float(value)
        if val > 600:
            val = val / 60  # Assume seconds
        return min(val, 600) if val >= 0 else None

    text = str(value).strip()
    if not text:
        return None

    # H:MM or HH:MM or HH:MM:SS
    time_match = re.match(r"^(\d+):(\d{2})(?::(\d{2}))?$", text)
    if time_match:
        h, m, s = int(time_match.group(1)), int(time_match.group(2)), time_match.group(3)
        total = h * 60 + m + (int(s) / 60 if s else 0)
        return min(total, 600) if total >= 0 else None

    # "45 min", "1h 30min", "1h30", "1 h 30 m"
    text_lower = text.lower()
    hours = 0.0
    minutes = 0.0

    h_match = re.search(r"(\d+)\s*h(?:our)?s?(?:\s|$|m)", text_lower)
    if h_match:
        hours = float(h_match.group(1))

    m_match = re.search(r"(\d+)\s*m(?:in)?(?:ute)?s?(?:\s|$)", text_lower)
    if m_match:
        minutes = float(m_match.group(1))

    # "1h30" without space: match (\d+)h(\d+)
    if hours == 0 and minutes == 0:
        hm_match = re.search(r"(\d+)\s*h\s*(\d+)", text_lower)
        if hm_match:
            hours = float(hm_match.group(1))
            minutes = float(hm_match.group(2))

    if hours > 0 or minutes > 0:
        total = hours * 60 + minutes
        return min(total, 600) if total >= 0 else None

    # Plain number
    parsed = parse_number(text)
    if parsed is not None:
        if parsed > 600:
            parsed = parsed / 60  # Assume seconds
        return min(parsed, 600) if parsed >= 0 else None
    return None
