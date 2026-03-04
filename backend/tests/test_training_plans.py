"""Tests for Daniels and Pfitzinger training plan generators."""
import pytest
from datetime import date
from app.services.training_plans.daniels import generate_daniels_plan, vdot_paces
from app.services.training_plans.pfitzinger import generate_pfitzinger_plan


class TestVdotPaces:
    def test_vdot_paces_vdot50(self):
        paces = vdot_paces(50)
        # At VDOT 50: Easy ~5:30/km, Threshold ~4:10/km, Marathon ~4:35/km
        assert 300 < paces["easy"] < 370        # 5:00–6:10 /km
        assert 230 < paces["threshold"] < 280   # 3:50–4:40 /km
        assert 250 < paces["marathon"] < 310    # 4:10–5:10 /km

    def test_faster_vdot_faster_paces(self):
        p50 = vdot_paces(50)
        p60 = vdot_paces(60)
        assert p60["threshold"] < p50["threshold"]
        assert p60["easy"] < p50["easy"]

    def test_zone_ordering(self):
        paces = vdot_paces(50)
        assert paces["easy"] > paces["marathon"] > paces["threshold"] > paces["interval"]


class TestDanielsPlan:
    def test_marathon_plan_length(self):
        plan = generate_daniels_plan(
            goal_distance="marathon",
            goal_race_date=date(2026, 10, 1),
            target_vdot=50.0,
        )
        assert len(plan) == 18 * 7

    def test_5k_plan(self):
        plan = generate_daniels_plan(
            goal_distance="5k",
            goal_race_date=date(2026, 6, 1),
            target_vdot=45.0,
        )
        assert len(plan) > 0
        assert all("workout_type" in w for w in plan)
        assert all("scheduled_date" in w for w in plan)

    def test_plan_has_required_fields(self):
        plan = generate_daniels_plan("marathon", date(2026, 10, 1), 50.0)
        w = plan[0]
        for field in ("scheduled_date", "week_number", "workout_type",
                      "description", "target_distance_m", "target_pace_s_per_km"):
            assert field in w

    def test_ends_on_race_date(self):
        race_date = date(2026, 10, 1)
        plan = generate_daniels_plan("marathon", race_date, 50.0)
        assert plan[-1]["scheduled_date"] == race_date


class TestPfitzingerPlan:
    def test_18_55_length(self):
        plan = generate_pfitzinger_plan(
            goal_race_date=date(2026, 10, 4),
            peak_weekly_km=88,
        )
        assert len(plan) == 18 * 7

    def test_has_long_runs(self):
        plan = generate_pfitzinger_plan(date(2026, 10, 4), peak_weekly_km=88)
        long_runs = [w for w in plan if w["workout_type"] == "long"]
        assert len(long_runs) >= 10

    def test_has_marathon_pace_runs(self):
        plan = generate_pfitzinger_plan(date(2026, 10, 4), peak_weekly_km=88)
        mp_runs = [w for w in plan if w["workout_type"] == "marathon_pace"]
        assert len(mp_runs) >= 4

    def test_scaling(self):
        plan_full = generate_pfitzinger_plan(date(2026, 10, 4), peak_weekly_km=88)
        plan_half = generate_pfitzinger_plan(date(2026, 10, 4), peak_weekly_km=44)
        full_dists = [w["target_distance_m"] for w in plan_full if w["target_distance_m"]]
        half_dists = [w["target_distance_m"] for w in plan_half if w["target_distance_m"]]
        # Half-peak plan should have half the total distance
        assert abs(sum(half_dists) / sum(full_dists) - 0.5) < 0.01
