"""PDF reader adapter."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, Union

from pypdf import PdfReader

from emagrecimento.application.interfaces import IPdfReader


class PypdfPdfReader(IPdfReader):
    """Extract text from PDF using pypdf."""

    def extract_text(self, source: Union[str, Path, BinaryIO]) -> str:
        reader = PdfReader(source)
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)
