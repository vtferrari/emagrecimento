"""Unit tests for Withings ZIP domain entities."""

from __future__ import annotations

import pytest

from emagrecimento.domain.withings_zip import (
    WithingsActivityDay,
    WithingsBodySnapshot,
    WithingsEcgReading,
    WithingsHealthRecord,
    WithingsSleepNight,
)


class TestWithingsBodySnapshot:
    """Tests for WithingsBodySnapshot."""

    def test_creates_snapshot_with_required_fields(self) -> None:
        s = WithingsBodySnapshot(
            date="2026-01-20",
            weight_kg=95.4,
            fat_mass_kg=23.5,
            muscle_mass_kg=68.4,
            visceral_fat=3.5,
            metabolic_age=38,
        )
        assert s.date == "2026-01-20"
        assert s.weight_kg == 95.4
        assert s.fat_mass_kg == 23.5
        assert s.muscle_mass_kg == 68.4
        assert s.visceral_fat == 3.5
        assert s.metabolic_age == 38

    def test_optional_fields_default_to_none(self) -> None:
        s = WithingsBodySnapshot(
            date="2026-01-20",
            weight_kg=95.4,
            fat_mass_kg=23.5,
            muscle_mass_kg=68.4,
            visceral_fat=3.5,
            metabolic_age=38,
        )
        assert s.bone_mass_kg is None
        assert s.water_pct is None
        assert s.bmr_kcal is None
        assert s.fat_free_mass_kg is None


class TestWithingsSleepNight:
    """Tests for WithingsSleepNight."""

    def test_creates_sleep_night_with_durations_in_hours(self) -> None:
        s = WithingsSleepNight(
            date="2026-01-19",
            total_h=6.9,
            light_h=4.1,
            deep_h=1.1,
            rem_h=2.5,
            awake_h=0.7,
            hr_min=59,
            hr_max=102,
            hr_avg=69,
        )
        assert s.date == "2026-01-19"
        assert s.total_h == 6.9
        assert s.light_h == 4.1
        assert s.deep_h == 1.1
        assert s.rem_h == 2.5
        assert s.awake_h == 0.7
        assert s.hr_min == 59
        assert s.hr_max == 102
        assert s.hr_avg == 69


class TestWithingsActivityDay:
    """Tests for WithingsActivityDay."""

    def test_creates_activity_day(self) -> None:
        a = WithingsActivityDay(date="2026-01-20", steps=15000)
        assert a.date == "2026-01-20"
        assert a.steps == 15000


class TestWithingsEcgReading:
    """Tests for WithingsEcgReading."""

    def test_creates_ecg_reading(self) -> None:
        e = WithingsEcgReading(date="2026-01-20", hr=87, value=9)
        assert e.date == "2026-01-20"
        assert e.hr == 87
        assert e.value == 9


class TestWithingsHealthRecord:
    """Tests for WithingsHealthRecord aggregate."""

    def test_delta_weight_from_first_to_latest(self) -> None:
        body = [
            WithingsBodySnapshot(
                date="2026-01-20",
                weight_kg=95.4,
                fat_mass_kg=23.5,
                muscle_mass_kg=68.4,
                visceral_fat=3.5,
                metabolic_age=38,
            ),
            WithingsBodySnapshot(
                date="2026-03-08",
                weight_kg=89.8,
                fat_mass_kg=12.5,
                muscle_mass_kg=73.5,
                visceral_fat=2.1,
                metabolic_age=30,
            ),
        ]
        record = WithingsHealthRecord(
            body_snapshots=body,
            sleep_nights=[],
            activity_days=[],
            ecg_readings=[],
        )
        assert record.delta_weight == pytest.approx(-5.6, abs=0.01)
        assert record.delta_fat_mass == pytest.approx(-11.0, abs=0.01)
        assert record.delta_muscle_mass == pytest.approx(5.1, abs=0.01)
        assert record.delta_visceral_fat == pytest.approx(-1.4, abs=0.01)
        assert record.delta_metabolic_age == -8

    def test_fat_mass_pct_from_latest(self) -> None:
        body = [
            WithingsBodySnapshot(
                date="2026-03-08",
                weight_kg=89.8,
                fat_mass_kg=12.5,
                muscle_mass_kg=73.5,
                visceral_fat=2.1,
                metabolic_age=30,
            ),
        ]
        record = WithingsHealthRecord(
            body_snapshots=body,
            sleep_nights=[],
            activity_days=[],
            ecg_readings=[],
        )
        assert record.fat_mass_pct == pytest.approx(13.9, abs=0.1)

    def test_avg_daily_steps_excludes_outliers_over_100k(self) -> None:
        activity = [
            WithingsActivityDay(date="2026-01-20", steps=15000),
            WithingsActivityDay(date="2026-01-21", steps=18000),
            WithingsActivityDay(date="2026-01-22", steps=150000),  # outlier
        ]
        record = WithingsHealthRecord(
            body_snapshots=[],
            sleep_nights=[],
            activity_days=activity,
            ecg_readings=[],
        )
        # Average of 15000 and 18000 only (outlier excluded)
        assert record.avg_daily_steps == 16500

    def test_avg_sleep_h_from_nights(self) -> None:
        nights = [
            WithingsSleepNight(
                date="2026-01-19",
                total_h=7.0,
                light_h=3.5,
                deep_h=1.5,
                rem_h=1.8,
                awake_h=0.5,
                hr_min=55,
                hr_max=80,
                hr_avg=62,
            ),
            WithingsSleepNight(
                date="2026-01-20",
                total_h=7.4,
                light_h=3.7,
                deep_h=1.4,
                rem_h=1.9,
                awake_h=0.4,
                hr_min=54,
                hr_max=75,
                hr_avg=60,
            ),
        ]
        record = WithingsHealthRecord(
            body_snapshots=[],
            sleep_nights=nights,
            activity_days=[],
            ecg_readings=[],
        )
        assert record.avg_sleep_h == pytest.approx(7.2, abs=0.01)

    def test_empty_record_returns_none_for_computed_props(self) -> None:
        record = WithingsHealthRecord(
            body_snapshots=[],
            sleep_nights=[],
            activity_days=[],
            ecg_readings=[],
        )
        assert record.delta_weight is None
        assert record.delta_fat_mass is None
        assert record.delta_muscle_mass is None
        assert record.delta_visceral_fat is None
        assert record.delta_metabolic_age is None
        assert record.fat_mass_pct is None
        assert record.avg_daily_steps is None
        assert record.avg_sleep_h is None
