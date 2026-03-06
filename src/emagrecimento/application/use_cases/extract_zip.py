"""Extract ZIP data use case."""

from __future__ import annotations

from typing import BinaryIO, Union

from emagrecimento.application.interfaces import IZipReader
from emagrecimento.domain.entities import ZipData


class ExtractZipDataUseCase:
    """Extract ZipData from MyFitnessPal export."""

    def __init__(self, zip_reader: IZipReader) -> None:
        self._zip_reader = zip_reader

    def execute(self, source: Union[str, BinaryIO]) -> ZipData:
        """Extract and return ZipData from ZIP source."""
        return self._zip_reader.extract(source)
