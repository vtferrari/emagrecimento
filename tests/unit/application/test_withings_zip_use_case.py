"""Unit tests for GetWithingsZipDataUseCase."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from emagrecimento.application.use_cases.get_withings_zip import GetWithingsZipDataUseCase
from emagrecimento.domain.withings_zip import WithingsHealthRecord


class TestGetWithingsZipDataUseCase:
    """Tests for GetWithingsZipDataUseCase."""

    def test_returns_none_when_zip_bytes_is_none(self) -> None:
        repo = MagicMock()
        use_case = GetWithingsZipDataUseCase(repository=repo)
        result = use_case.execute(None)
        assert result is None
        repo.load.assert_not_called()

    def test_returns_repository_result_when_zip_provided(self) -> None:
        record = WithingsHealthRecord(
            body_snapshots=(),
            sleep_nights=(),
            activity_days=(),
            ecg_readings=(),
        )
        repo = MagicMock()
        repo.load.return_value = record
        use_case = GetWithingsZipDataUseCase(repository=repo)

        result = use_case.execute(b"fake_zip_bytes")

        assert result is record
        repo.load.assert_called_once_with(b"fake_zip_bytes")

    def test_returns_none_when_repository_returns_none(self) -> None:
        repo = MagicMock()
        repo.load.return_value = None
        use_case = GetWithingsZipDataUseCase(repository=repo)

        result = use_case.execute(b"invalid_zip")

        assert result is None
