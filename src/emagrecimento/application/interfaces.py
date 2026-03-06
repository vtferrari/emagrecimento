"""Application interfaces (ports) - abstract dependencies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, BinaryIO, Union

from emagrecimento.domain.entities import ZipData


class IZipReader(ABC):
    """Port for reading ZIP export data."""

    @abstractmethod
    def extract(self, source: Union[str, BinaryIO]) -> ZipData:
        """Extract ZipData from ZIP file path or stream."""
        ...


class IPdfReader(ABC):
    """Port for reading PDF text."""

    @abstractmethod
    def extract_text(self, source: Union[str, BinaryIO]) -> str:
        """Extract raw text from PDF."""
        ...


class IPdfMetricsParser(ABC):
    """Port for parsing Withings metrics from PDF text."""

    @abstractmethod
    def parse(self, text: str) -> dict[str, Any]:
        """Parse metrics from PDF text. Returns dict of metric name -> value."""
        ...
