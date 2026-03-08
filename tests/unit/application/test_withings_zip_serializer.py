"""Unit tests for Withings ZIP serializer."""

from __future__ import annotations

from emagrecimento.application.serializers.withings_zip import withings_health_record_to_dict
from emagrecimento.domain.withings_zip import (
    WithingsHealthRecord,
    WithingsSleepNight,
)


class TestWithingsZipSerializer:
    """Tests for withings_health_record_to_dict."""

    def test_avg_hr_mean_from_hr_average_column(self) -> None:
        """avg_hr_mean must be computed from HR average (hr_avg), not Min HR. Expect 62.5."""
        nights = (
            WithingsSleepNight(
                date="2026-01-19",
                total_h=8.4,
                light_h=4.1,
                deep_h=1.1,
                rem_h=2.5,
                awake_h=0.7,
                hr_min=42,
                hr_max=102,
                hr_avg=60,
            ),
            WithingsSleepNight(
                date="2026-01-20",
                total_h=8.2,
                light_h=4.0,
                deep_h=1.0,
                rem_h=2.5,
                awake_h=0.7,
                hr_min=43,
                hr_max=98,
                hr_avg=65,
            ),
        )
        record = WithingsHealthRecord(
            body_snapshots=(),
            sleep_nights=nights,
            activity_days=(),
            ecg_readings=(),
        )
        result = withings_health_record_to_dict(record)
        assert result["sleep"]["summary"]["avg_hr_mean"] == 62.5
        assert result["sleep"]["summary"]["avg_hr_min"] == 42.5

    def test_avg_hr_mean_excludes_nights_with_zero_hr(self) -> None:
        """Nights with hr_avg=0 (invalid) are excluded from avg_hr_mean."""
        nights = (
            WithingsSleepNight(
                date="2026-01-19",
                total_h=8.0,
                light_h=4.0,
                deep_h=1.0,
                rem_h=2.0,
                awake_h=1.0,
                hr_min=0,
                hr_max=0,
                hr_avg=0,
            ),
            WithingsSleepNight(
                date="2026-01-20",
                total_h=8.0,
                light_h=4.0,
                deep_h=1.0,
                rem_h=2.0,
                awake_h=1.0,
                hr_min=55,
                hr_max=95,
                hr_avg=62,
            ),
        )
        record = WithingsHealthRecord(
            body_snapshots=(),
            sleep_nights=nights,
            activity_days=(),
            ecg_readings=(),
        )
        result = withings_health_record_to_dict(record)
        assert result["sleep"]["summary"]["avg_hr_mean"] == 62.0
