"""Extract PDF metrics use case."""

from __future__ import annotations

from typing import Any, BinaryIO, Union

from emagrecimento.application.interfaces import IPdfMetricsParser, IPdfReader


class ExtractPdfMetricsUseCase:
    """Extract Withings metrics from PDF."""

    def __init__(self, pdf_reader: IPdfReader, metrics_parser: IPdfMetricsParser) -> None:
        self._pdf_reader = pdf_reader
        self._metrics_parser = metrics_parser

    def execute(self, source: Union[str, BinaryIO]) -> dict[str, Any]:
        """Extract text from PDF and parse metrics."""
        text = self._pdf_reader.extract_text(source)
        return self._metrics_parser.parse(text)
