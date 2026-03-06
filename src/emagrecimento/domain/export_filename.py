"""Export filename builder for JSON report download."""

from __future__ import annotations

import re
from datetime import datetime


def build_export_filename(name: str | None, when: datetime | None = None) -> str:
    """
    Build export filename: {name}_{YYYY-MM-DD}_{HH-mm-ss}.json

    - name: user name (spaces -> underscore, invalid chars removed). Fallback: 'relatorio'
    - when: extraction timestamp (default: now)
    """
    raw = (name or "").strip()
    if raw:
        name_part = raw.replace(" ", "_")
        name_part = re.sub(r'[/\\:*?"<>|]', "", name_part)
    else:
        name_part = "relatorio"

    dt = when or datetime.now()
    date_part = (
        f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}_"
        f"{dt.hour:02d}-{dt.minute:02d}-{dt.second:02d}"
    )
    return f"{name_part}_{date_part}.json"
