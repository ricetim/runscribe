"""Tests for the analytics service."""
import math
from datetime import datetime, date, timedelta
import pytest

from app.services.analytics import (
    compute_vdot,
    predict_race_time_s,
    compute_pace_zones,
    compute_gap,
    compute_trimp,
    compute_hrtss,
    compute_training_loads,
    PaceZones,
    TrainingLoad,
)


class TestComputeVdot:
    def test_known_value_10k(self):
        # 35:21.6 for 10,000m → VDOT ≈ 60.0 (from Oxygen Power Table 1)
        vdot = compute_vdot(10000, 35 * 60 + 21.6)
        assert abs(vdot - 60.0) < 0.5

    def test_known_value_5k(self):
        # 17:03 for 5000m → VDOT ≈ 60.0 (equivalent performance)
        vdot = compute_vdot(5000, 17 * 60 + 3)
        assert abs(vdot - 60.0) < 1.0

    def test_faster_runner_higher_vdot(self):
        slow = compute_vdot(10000, 50 * 60)
        fast = compute_vdot(10000, 35 * 60)
        assert fast > slow

    def test_invalid_inputs(self):
        with pytest.raises(ValueError):
            compute_vdot(0, 3600)
        with pytest.raises(ValueError):
            compute_vdot(5000, 0)

    def test_returns_float(self):
        assert isinstance(compute_vdot(5000, 1200), float)


class TestPredictRaceTime:
    def test_roundtrip_10k(self):
        # Compute VDOT from 10K time, then predict 10K time back
        original_s = 35 * 60 + 21.6
        vdot = compute_vdot(10000, original_s)
        predicted = predict_race_time_s(vdot, 10000)
        assert abs(predicted - original_s) < 5  # within 5 seconds

    def test_roundtrip_marathon(self):
        original_s = 3 * 3600 + 30 * 60  # 3:30 marathon
        vdot = compute_vdot(42195, original_s)
        predicted = predict_race_time_s(vdot, 42195)
        assert abs(predicted - original_s) < 30  # within 30 seconds

    def test_longer_distance_takes_longer(self):
        vdot = 50.0
        t_5k = predict_race_time_s(vdot, 5000)
        t_10k = predict_race_time_s(vdot, 10000)
        assert t_10k > t_5k * 2  # 10K should be >2x the 5K time

    def test_invalid_inputs(self):
        with pytest.raises(ValueError):
            predict_race_time_s(0, 5000)
        with pytest.raises(ValueError):
            predict_race_time_s(50, 0)


class TestComputePaceZones:
    def test_returns_pace_zones(self):
        zones = compute_pace_zones(50.0)
        assert isinstance(zones, PaceZones)

    def test_zone_ordering(self):
        # Faster zones (T, I, R) should have lower s/km values
        zones = compute_pace_zones(50.0)
        assert zones.easy_lo > zones.easy_hi      # slow end is slower
        assert zones.easy_hi > zones.marathon      # M faster than E
        assert zones.marathon > zones.threshold    # T faster than M
        assert zones.threshold > zones.interval    # I faster than T
        assert zones.interval > zones.repetition   # R fastest

    def test_vdot60_easy_pace_range(self):
        # VDOT 60 easy pace should be roughly 4:30-5:30/km
        zones = compute_pace_zones(60.0)
        assert 240 < zones.easy_hi < 360   # 4:00-6:00/km
        assert 270 < zones.easy_lo < 420   # slower end

    def test_higher_vdot_faster_paces(self):
        z50 = compute_pace_zones(50.0)
        z60 = compute_pace_zones(60.0)
        assert z60.threshold < z50.threshold  # VDOT 60 has faster T pace


class TestComputeGap:
    def test_flat_ground_unchanged(self):
        pace = 300.0  # 5:00/km
        assert abs(compute_gap(pace, 0.0) - pace) < 0.01

    def test_uphill_slower_gap(self):
        # Uphill actual pace of 360 s/km should give faster (lower) GAP
        pace = 360.0
        gap = compute_gap(pace, 0.10)  # 10% uphill
        assert gap < pace

    def test_downhill_faster_gap(self):
        # Downhill actual pace should give slower (higher) GAP
        pace = 240.0
        gap = compute_gap(pace, -0.10)  # 10% downhill
        assert gap > pace


class TestComputeTrimp:
    def _make_dps(self, hr_values, duration_min=1.0):
        """Make minimal datapoint dicts with timestamps."""
        base = datetime(2024, 1, 1, 0, 0, 0)
        dps = []
        for i, hr in enumerate(hr_values):
            dps.append({
                "heart_rate": hr,
                "timestamp": base + timedelta(minutes=i * duration_min),
            })
        return dps

    def test_zero_for_empty(self):
        assert compute_trimp([], 50, 190) == 0.0

    def test_positive_for_exercise(self):
        dps = self._make_dps([140, 145, 150, 148, 142])
        trimp = compute_trimp(dps, hr_rest=50, hr_max=190)
        assert trimp > 0

    def test_higher_hr_more_trimp(self):
        dps_easy = self._make_dps([120] * 10)
        dps_hard = self._make_dps([160] * 10)
        t_easy = compute_trimp(dps_easy, 50, 190)
        t_hard = compute_trimp(dps_hard, 50, 190)
        assert t_hard > t_easy

    def test_female_less_trimp(self):
        dps = self._make_dps([150] * 10)
        t_male = compute_trimp(dps, 50, 190, sex="male")
        t_female = compute_trimp(dps, 50, 190, sex="female")
        assert t_male > t_female


class TestComputeHrtss:
    def test_zero_trimp_zero_tss(self):
        assert compute_hrtss(0.0) == 0.0

    def test_one_hour_at_threshold(self):
        # TRIMP for 1 hour at LTHR (delta_HR ≈ 0.64 for typical runner) ≈ 131.7 → TSS ≈ 100
        approx_trimp = 131.7
        tss = compute_hrtss(approx_trimp)
        assert abs(tss - 100.0) < 5.0

    def test_scaling(self):
        assert compute_hrtss(200.0) > compute_hrtss(100.0)


class TestComputeTrainingLoads:
    def test_empty_returns_empty(self):
        assert compute_training_loads({}) == {}

    def test_rest_day_decays(self):
        # One day of work, then rest — CTL should decrease
        d1 = date(2024, 1, 1)
        d2 = date(2024, 1, 2)
        loads = compute_training_loads({d1: 100.0, d2: 0.0})
        assert loads[d2].ctl < loads[d1].ctl

    def test_consecutive_hard_days_increase_atl(self):
        tss_by_date = {date(2024, 1, 1) + timedelta(days=i): 100.0 for i in range(14)}
        loads = compute_training_loads(tss_by_date)
        dates = sorted(loads.keys())
        assert loads[dates[-1]].atl > loads[dates[0]].atl

    def test_tsb_is_ctl_minus_atl(self):
        tss = {date(2024, 1, 1) + timedelta(days=i): 80.0 for i in range(30)}
        loads = compute_training_loads(tss)
        for d, load in loads.items():
            assert abs(load.tsb - (load.ctl - load.atl)) < 1e-9

    def test_atl_responds_faster_than_ctl(self):
        # After a single hard day, ATL should be higher relative to CTL
        d = date(2024, 1, 1)
        loads = compute_training_loads({d: 200.0})
        assert loads[d].atl > loads[d].ctl

    def test_returns_training_load_objects(self):
        d = date(2024, 1, 1)
        loads = compute_training_loads({d: 50.0})
        assert isinstance(loads[d], TrainingLoad)
