"""Unit tests for WithingsZipAdapter."""

from __future__ import annotations

import io
import zipfile

import pytest

from emagrecimento.domain.withings_zip import (
    WithingsActivityDay,
    WithingsBodySnapshot,
    WithingsHealthRecord,
    WithingsSleepNight,
)
from emagrecimento.infrastructure.withings_zip_adapter import WithingsZipAdapter


def make_fake_zip(
    measures_csv: str = "",
    sleep_csv: str = "",
    steps_csv: str = "",
    ecg_csv: str | None = None,
) -> bytes:
    """Create synthetic Withings ZIP in memory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        if measures_csv:
            zf.writestr("Measures | [2026-01-01] - [2026-01-31].csv", measures_csv)
        if sleep_csv:
            zf.writestr("Sleep | [2026-01-01] - [2026-01-31].csv", sleep_csv)
        if steps_csv:
            zf.writestr("Steps | [2026-01-01] - [2026-01-31].csv", steps_csv)
        if ecg_csv:
            zf.writestr("Signals | [2026-01-01] - [2026-01-31]/[2026-01-20] [07:26 AM] | ECG.csv", ecg_csv)
    return buf.getvalue()


class TestWithingsZipAdapter:
    """Tests for WithingsZipAdapter."""

    def test_returns_none_when_zip_bytes_is_none(self) -> None:
        adapter = WithingsZipAdapter()
        assert adapter.load(None) is None

    def test_returns_none_when_zip_is_empty_or_invalid(self) -> None:
        adapter = WithingsZipAdapter()
        assert adapter.load(b"") is None
        assert adapter.load(b"not a zip") is None

    def test_returns_none_when_no_required_files(self) -> None:
        """ZIP with no Measures/Sleep/Steps files returns None."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("other.csv", "a,b\n1,2\n")
        adapter = WithingsZipAdapter()
        result = adapter.load(buf.getvalue())
        assert result is None

    def test_parses_measures_csv(self) -> None:
        measures = (
            "Date,Time,Value,Unit,Recorded by,Measure type\n"
            "2026-01-20,08:00,95.4,kg,Scale,Weight\n"
            "2026-01-20,08:00,23.5,kg,Scale,Fat Mass Weight\n"
            "2026-01-20,08:00,68.4,kg,Scale,Muscle Mass\n"
            "2026-01-20,08:00,3.5,,Scale,Visceral Fat\n"
            "2026-01-20,08:00,38,years,Scale,Metabolic Age\n"
            "2026-01-21,08:00,95.0,kg,Scale,Weight\n"
        )
        zip_bytes = make_fake_zip(measures_csv=measures)
        adapter = WithingsZipAdapter()
        result = adapter.load(zip_bytes)
        assert result is not None
        assert len(result.body_snapshots) >= 2
        first = result.body_snapshots[0]
        assert first.date == "2026-01-20"
        assert first.weight_kg == 95.4
        assert first.fat_mass_kg == 23.5
        assert first.muscle_mass_kg == 68.4
        assert first.visceral_fat == 3.5
        assert first.metabolic_age == 38

    def test_parses_sleep_csv_converts_seconds_to_hours(self) -> None:
        # Light 14760s=4.1h, Deep 3960s=1.1h, REM 9000s=2.5h, Awake 2520s=0.7h
        # Total = 14760+3960+9000+2520 = 30240s = 8.4h
        sleep = (
            "Date,End date,Start Date,Time to sleep,Time to wake,Light duration,Deep duration,REM duration,Awake duration,Nb awake,Min HR,Max HR,HR average\n"
            "2026-01-19,2026-01-20,2026-01-19,300,25200,14760,3960,9000,2520,2,59,102,69\n"
        )
        zip_bytes = make_fake_zip(sleep_csv=sleep)
        adapter = WithingsZipAdapter()
        result = adapter.load(zip_bytes)
        assert result is not None
        assert len(result.sleep_nights) == 1
        night = result.sleep_nights[0]
        assert night.date == "2026-01-19"
        assert night.total_h == pytest.approx(8.4, abs=0.1)
        assert night.light_h == pytest.approx(4.1, abs=0.1)
        assert night.deep_h == pytest.approx(1.1, abs=0.1)
        assert night.rem_h == pytest.approx(2.5, abs=0.1)
        assert night.awake_h == pytest.approx(0.7, abs=0.1)
        assert night.hr_min == 59
        assert night.hr_max == 102
        assert night.hr_avg == 69

    def test_parses_steps_csv_groups_by_date(self) -> None:
        steps = (
            "Date,Measure type,Value\n"
            "2026-01-20,Steps,15000\n"
            "2026-01-20,Steps,500\n"
            "2026-01-21,Steps,18000\n"
        )
        zip_bytes = make_fake_zip(steps_csv=steps)
        adapter = WithingsZipAdapter()
        result = adapter.load(zip_bytes)
        assert result is not None
        assert len(result.activity_days) == 2
        by_date = {a.date: a.steps for a in result.activity_days}
        assert by_date["2026-01-20"] == 15500
        assert by_date["2026-01-21"] == 18000

    def test_steps_excludes_outliers_over_100k(self) -> None:
        steps = (
            "Date,Measure type,Value\n"
            "2026-01-20,Steps,15000\n"
            "2026-01-21,Steps,150000\n"
        )
        zip_bytes = make_fake_zip(steps_csv=steps)
        adapter = WithingsZipAdapter()
        result = adapter.load(zip_bytes)
        assert result is not None
        # Day with 150k should be excluded from activity_days
        assert result.avg_daily_steps == 15000

    def test_parses_ecg_csv(self) -> None:
        ecg = "date,time,HR,QRS,PR,QT,QTc,value,signal\n2026-01-20,07:26,87,95,150,380,420,9,ignore_this\n"
        zip_bytes = make_fake_zip(ecg_csv=ecg)
        adapter = WithingsZipAdapter()
        result = adapter.load(zip_bytes)
        assert result is not None
        assert len(result.ecg_readings) == 1
        ecg_r = result.ecg_readings[0]
        assert ecg_r.date == "2026-01-20"
        assert ecg_r.hr == 87
        assert ecg_r.value == 9

    def test_sleep_treats_dash_as_nan(self) -> None:
        sleep = (
            "Date,End date,Start Date,Time to sleep,Time to wake,Light duration,Deep duration,REM duration,Awake duration,Nb awake,Min HR,Max HR,HR average\n"
            "2026-01-19,2026-01-20,2026-01-19,-,-,-,3960,9000,2520,2,59,102,69\n"
        )
        zip_bytes = make_fake_zip(sleep_csv=sleep)
        adapter = WithingsZipAdapter()
        result = adapter.load(zip_bytes)
        assert result is not None
        # Should not crash; missing values handled
        assert len(result.sleep_nights) == 1

    def test_sleep_hr_average_reads_correct_column_not_min_hr(self) -> None:
        """HR average column must be used for hr_avg, not Min HR. avg_hr_mean should be ~62.5."""
        sleep = (
            "Date,End date,Start Date,Time to sleep,Time to wake,Light duration,Deep duration,REM duration,Awake duration,Nb awake,Min HR,Max HR,HR average\n"
            "2026-01-19,2026-01-20,2026-01-19,300,25200,14760,3960,9000,2520,2,42,102,60\n"
            "2026-01-20,2026-01-21,2026-01-20,300,25200,14760,3960,9000,2520,2,43,98,65\n"
        )
        zip_bytes = make_fake_zip(sleep_csv=sleep)
        adapter = WithingsZipAdapter()
        result = adapter.load(zip_bytes)
        assert result is not None
        assert len(result.sleep_nights) == 2
        # hr_avg must come from HR average (60, 65), not Min HR (42, 43)
        assert result.sleep_nights[0].hr_avg == 60
        assert result.sleep_nights[1].hr_avg == 65
        assert result.sleep_nights[0].hr_min == 42
        assert result.sleep_nights[1].hr_min == 43

    def test_sleep_parses_alternative_hr_average_column_name(self) -> None:
        """Withings export may use 'Average heart rate' instead of 'HR average'."""
        sleep = (
            "Date,Light duration,Deep duration,REM duration,Awake duration,Min HR,Max HR,Average heart rate\n"
            "2026-01-19,14760,3960,9000,2520,42,102,62\n"
        )
        zip_bytes = make_fake_zip(sleep_csv=sleep)
        adapter = WithingsZipAdapter()
        result = adapter.load(zip_bytes)
        assert result is not None
        assert len(result.sleep_nights) == 1
        assert result.sleep_nights[0].hr_avg == 62
        assert result.sleep_nights[0].hr_min == 42

    def test_returns_json_safe_types(self) -> None:
        """All values must be Python native (no numpy.int64, datetime, NaN)."""
        measures = "Date,Time,Value,Unit,Recorded by,Measure type\n2026-01-20,08:00,95.4,kg,Scale,Weight\n"
        zip_bytes = make_fake_zip(measures_csv=measures)
        adapter = WithingsZipAdapter()
        result = adapter.load(zip_bytes)
        assert result is not None
        for s in result.body_snapshots:
            assert isinstance(s.date, str)
            assert isinstance(s.weight_kg, (int, float))
        for a in result.activity_days:
            assert isinstance(a.steps, int)
