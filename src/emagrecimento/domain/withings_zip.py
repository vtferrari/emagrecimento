"""Domain entities for Withings ZIP export data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WithingsBodySnapshot:
    """Body composition snapshot for a single day."""

    date: str
    weight_kg: float
    fat_mass_kg: float
    muscle_mass_kg: float
    visceral_fat: float
    metabolic_age: int
    bone_mass_kg: float | None = None
    water_pct: float | None = None
    bmr_kcal: int | None = None
    fat_free_mass_kg: float | None = None


@dataclass(frozen=True)
class WithingsSleepNight:
    """Sleep data for a single night (durations already in hours)."""

    date: str
    total_h: float
    light_h: float
    deep_h: float
    rem_h: float
    awake_h: float
    hr_min: int
    hr_max: int
    hr_avg: int


@dataclass(frozen=True)
class WithingsActivityDay:
    """Steps for a single day."""

    date: str
    steps: int


@dataclass(frozen=True)
class WithingsEcgReading:
    """ECG reading result (value 9 = normal sinus rhythm)."""

    date: str
    hr: int
    value: int


@dataclass(frozen=True)
class WithingsHealthRecord:
    """Aggregate root with all Withings ZIP data and computed properties."""

    body_snapshots: tuple[WithingsBodySnapshot, ...]
    sleep_nights: tuple[WithingsSleepNight, ...]
    activity_days: tuple[WithingsActivityDay, ...]
    ecg_readings: tuple[WithingsEcgReading, ...]

    @property
    def delta_weight(self) -> float | None:
        """Weight change from first to latest snapshot."""
        if len(self.body_snapshots) < 2:
            return None
        first = self.body_snapshots[0].weight_kg
        latest = self.body_snapshots[-1].weight_kg
        return round(latest - first, 2)

    @property
    def delta_fat_mass(self) -> float | None:
        """Fat mass change from first to latest snapshot."""
        if len(self.body_snapshots) < 2:
            return None
        first = self.body_snapshots[0].fat_mass_kg
        latest = self.body_snapshots[-1].fat_mass_kg
        return round(latest - first, 2)

    @property
    def delta_muscle_mass(self) -> float | None:
        """Muscle mass change from first to latest snapshot."""
        if len(self.body_snapshots) < 2:
            return None
        first = self.body_snapshots[0].muscle_mass_kg
        latest = self.body_snapshots[-1].muscle_mass_kg
        return round(latest - first, 2)

    @property
    def delta_visceral_fat(self) -> float | None:
        """Visceral fat change from first to latest snapshot."""
        if len(self.body_snapshots) < 2:
            return None
        first = self.body_snapshots[0].visceral_fat
        latest = self.body_snapshots[-1].visceral_fat
        return round(latest - first, 2)

    @property
    def delta_metabolic_age(self) -> int | None:
        """Metabolic age change from first to latest snapshot."""
        if len(self.body_snapshots) < 2:
            return None
        first = self.body_snapshots[0].metabolic_age
        latest = self.body_snapshots[-1].metabolic_age
        return latest - first

    @property
    def fat_mass_pct(self) -> float | None:
        """Fat mass percentage from latest snapshot (100 * fat_kg / weight_kg)."""
        if not self.body_snapshots:
            return None
        latest = self.body_snapshots[-1]
        if latest.weight_kg <= 0:
            return None
        return round(100 * latest.fat_mass_kg / latest.weight_kg, 1)

    @property
    def avg_daily_steps(self) -> float | None:
        """Average daily steps excluding outliers (>100k)."""
        valid = [a.steps for a in self.activity_days if a.steps <= 100_000]
        if not valid:
            return None
        return round(sum(valid) / len(valid), 0)

    @property
    def avg_sleep_h(self) -> float | None:
        """Average sleep duration in hours per night."""
        if not self.sleep_nights:
            return None
        total = sum(n.total_h for n in self.sleep_nights)
        return round(total / len(self.sleep_nights), 1)
