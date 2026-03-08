"""Get Withings ZIP data use case."""

from __future__ import annotations

from emagrecimento.application.interfaces import WithingsZipRepository
from emagrecimento.domain.withings_zip import WithingsHealthRecord


class GetWithingsZipDataUseCase:
    """Load Withings health data from ZIP export bytes."""

    def __init__(self, repository: WithingsZipRepository) -> None:
        self._repository = repository

    def execute(self, zip_bytes: bytes | None) -> WithingsHealthRecord | None:
        """Load and return WithingsHealthRecord from ZIP bytes. Returns None if invalid."""
        if zip_bytes is None:
            return None
        return self._repository.load(zip_bytes)
