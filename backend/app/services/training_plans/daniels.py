"""
Jack Daniels training plan generator.
Pace formulas from "Daniels' Running Formula" (4th ed., 2022).
VDOT pace tables computed from the original Daniels-Gilbert regression equations
(Oxygen Power, Daniels & Gilbert 1979).
"""
import math
from datetime import date, timedelta
from typing import Any


# ── VDOT pace computation ──────────────────────────────────────────────────

def _velocity_at_vdot_pct(vdot: float, pct: float) -> float:
    """Return velocity (m/min) for a given VDOT and % of VO2max."""
    # Solve: VO2(v) = -4.60 + 0.182258v + 0.000104v² for v, given VO2 = pct * vdot
    vo2_target = pct * vdot
    a, b, c = 0.000104, 0.182258, -4.60 - vo2_target
    disc = b**2 - 4 * a * c
    return (-b + math.sqrt(disc)) / (2 * a)


def vdot_paces(vdot: float) -> dict[str, float]:
    """
    Return training paces (seconds per km) for key zones at a given VDOT.
    Zone %VO2max midpoints from Daniels' Running Formula, Chapter 4.
    """
    zones = {
        "easy":        0.65,   # 59–74% VO2max, using 65% midpoint
        "marathon":    0.84,   # 75–84% VO2max
        "threshold":   0.88,   # 85–88% VO2max
        "interval":    0.975,  # 95–100% VO2max
        "repetition":  1.05,   # 105–120% VO2max
        "marathon_pace": 0.84, # alias
    }
    paces = {}
    for name, pct in zones.items():
        v = _velocity_at_vdot_pct(vdot, pct)   # m/min
        paces[name] = round(1000 / v * 60, 1)  # s/km
    return paces


# ── Plan templates ─────────────────────────────────────────────────────────
# Each week: list of (workout_type, distance_km, description)

_MARATHON_TEMPLATE_18W = [
    # Week 1 — base
    [("easy", 10, "Easy 10 km"), ("rest", 0, "Rest"), ("easy", 8, "Easy 8 km"),
     ("rest", 0, "Rest"), ("easy", 8, "Easy 8 km"), ("easy", 6, "Easy 6 km"),
     ("long", 16, "Long 16 km")],
    # Week 2
    [("easy", 10, "Easy 10 km"), ("rest", 0, "Rest"), ("threshold", 10, "10 km w/ 3 km @ T-pace"),
     ("rest", 0, "Rest"), ("easy", 8, "Easy 8 km"), ("easy", 6, "Easy 6 km"),
     ("long", 19, "Long 19 km")],
    # Week 3
    [("easy", 10, "Easy 10 km"), ("rest", 0, "Rest"), ("interval", 10, "10 km w/ 3×1600m @ I-pace"),
     ("rest", 0, "Rest"), ("easy", 8, "Easy 8 km"), ("easy", 6, "Easy 6 km"),
     ("long", 21, "Long 21 km")],
    # Week 4 — recovery
    [("easy", 8, "Easy 8 km"), ("rest", 0, "Rest"), ("easy", 6, "Easy 6 km"),
     ("rest", 0, "Rest"), ("easy", 6, "Easy 6 km"), ("easy", 5, "Easy 5 km"),
     ("long", 16, "Long 16 km")],
    # Week 5
    [("easy", 10, "Easy 10 km"), ("rest", 0, "Rest"), ("marathon_pace", 12, "12 km w/ 6 @ MP"),
     ("rest", 0, "Rest"), ("easy", 8, "Easy 8 km"), ("easy", 6, "Easy 6 km"),
     ("long", 22, "Long 22 km")],
    # Week 6
    [("easy", 10, "Easy 10 km"), ("rest", 0, "Rest"), ("threshold", 10, "10 km w/ 4 km @ T-pace"),
     ("rest", 0, "Rest"), ("easy", 8, "Easy 8 km"), ("easy", 6, "Easy 6 km"),
     ("long", 24, "Long 24 km")],
    # Week 7
    [("easy", 10, "Easy 10 km"), ("rest", 0, "Rest"), ("interval", 10, "10 km w/ 4×1200m @ I-pace"),
     ("rest", 0, "Rest"), ("easy", 8, "Easy 8 km"), ("easy", 6, "Easy 6 km"),
     ("long", 26, "Long 26 km")],
    # Week 8 — recovery
    [("easy", 8, "Easy 8 km"), ("rest", 0, "Rest"), ("easy", 6, "Easy 6 km"),
     ("rest", 0, "Rest"), ("easy", 6, "Easy 6 km"), ("easy", 5, "Easy 5 km"),
     ("long", 18, "Long 18 km")],
    # Week 9 — peak builds
    [("easy", 10, "Easy 10 km"), ("rest", 0, "Rest"), ("marathon_pace", 14, "14 km w/ 8 @ MP"),
     ("rest", 0, "Rest"), ("easy", 10, "Easy 10 km"), ("easy", 6, "Easy 6 km"),
     ("long", 27, "Long 27 km")],
    # Week 10
    [("easy", 10, "Easy 10 km"), ("rest", 0, "Rest"), ("threshold", 12, "12 km w/ 5 km @ T-pace"),
     ("rest", 0, "Rest"), ("easy", 10, "Easy 10 km"), ("easy", 6, "Easy 6 km"),
     ("long", 29, "Long 29 km")],
    # Week 11
    [("easy", 10, "Easy 10 km"), ("rest", 0, "Rest"), ("interval", 12, "12 km w/ 5×1000m @ I-pace"),
     ("rest", 0, "Rest"), ("easy", 10, "Easy 10 km"), ("easy", 6, "Easy 6 km"),
     ("long", 30, "Long 30 km")],
    # Week 12 — recovery
    [("easy", 8, "Easy 8 km"), ("rest", 0, "Rest"), ("easy", 6, "Easy 6 km"),
     ("rest", 0, "Rest"), ("easy", 6, "Easy 6 km"), ("easy", 5, "Easy 5 km"),
     ("long", 19, "Long 19 km")],
    # Week 13 — specificity
    [("easy", 10, "Easy 10 km"), ("rest", 0, "Rest"), ("marathon_pace", 16, "16 km w/ 10 @ MP"),
     ("rest", 0, "Rest"), ("easy", 10, "Easy 10 km"), ("easy", 6, "Easy 6 km"),
     ("long", 26, "Long 26 km")],
    # Week 14
    [("easy", 10, "Easy 10 km"), ("rest", 0, "Rest"), ("threshold", 10, "10 km w/ 4 km @ T-pace"),
     ("rest", 0, "Rest"), ("easy", 8, "Easy 8 km"), ("easy", 6, "Easy 6 km"),
     ("long", 22, "Long 22 km")],
    # Week 15
    [("easy", 8, "Easy 8 km"), ("rest", 0, "Rest"), ("marathon_pace", 12, "12 km w/ 6 @ MP"),
     ("rest", 0, "Rest"), ("easy", 8, "Easy 8 km"), ("easy", 6, "Easy 6 km"),
     ("long", 19, "Long 19 km")],
    # Week 16 — taper begins
    [("easy", 6, "Easy 6 km"), ("rest", 0, "Rest"), ("easy", 6, "Easy 6 km"),
     ("rest", 0, "Rest"), ("easy", 5, "Easy 5 km"), ("easy", 3, "Easy 3 km"),
     ("long", 16, "Long 16 km")],
    # Week 17 — taper
    [("easy", 6, "Easy 6 km"), ("rest", 0, "Rest"), ("marathon_pace", 8, "8 km w/ 4 @ MP"),
     ("rest", 0, "Rest"), ("easy", 5, "Easy 5 km"), ("easy", 3, "Easy 3 km"),
     ("long", 11, "Long 11 km")],
    # Week 18 — race week
    [("easy", 5, "Easy 5 km"), ("rest", 0, "Rest"), ("easy", 3, "Easy 3 km"),
     ("rest", 0, "Rest"), ("easy", 3, "Easy 3 km"), ("easy", 3, "Shakeout 3 km"),
     ("marathon_pace", 0, "Race day!")],
]

_5K_TEMPLATE_12W = [
    [("easy", 6, "Easy 6 km"), ("rest", 0, "Rest"), ("interval", 6, "6 km w/ 4×400m @ R-pace"),
     ("rest", 0, "Rest"), ("easy", 6, "Easy 6 km"), ("easy", 5, "Easy 5 km"),
     ("long", 10, "Long 10 km")],
    [("easy", 6, "Easy 6 km"), ("rest", 0, "Rest"), ("threshold", 6, "6 km w/ 2 km @ T-pace"),
     ("rest", 0, "Rest"), ("easy", 6, "Easy 6 km"), ("easy", 5, "Easy 5 km"),
     ("long", 12, "Long 12 km")],
    [("easy", 6, "Easy 6 km"), ("rest", 0, "Rest"), ("interval", 8, "8 km w/ 6×400m @ I-pace"),
     ("rest", 0, "Rest"), ("easy", 6, "Easy 6 km"), ("easy", 5, "Easy 5 km"),
     ("long", 13, "Long 13 km")],
    [("easy", 5, "Easy 5 km"), ("rest", 0, "Rest"), ("easy", 5, "Easy 5 km"),
     ("rest", 0, "Rest"), ("easy", 5, "Easy 5 km"), ("easy", 3, "Easy 3 km"),
     ("long", 10, "Long 10 km")],
    [("easy", 6, "Easy 6 km"), ("rest", 0, "Rest"), ("interval", 10, "10 km w/ 5×1000m @ I-pace"),
     ("rest", 0, "Rest"), ("easy", 6, "Easy 6 km"), ("easy", 5, "Easy 5 km"),
     ("long", 14, "Long 14 km")],
    [("easy", 6, "Easy 6 km"), ("rest", 0, "Rest"), ("threshold", 8, "8 km w/ 3 km @ T-pace"),
     ("rest", 0, "Rest"), ("easy", 6, "Easy 6 km"), ("easy", 5, "Easy 5 km"),
     ("long", 14, "Long 14 km")],
    [("easy", 6, "Easy 6 km"), ("rest", 0, "Rest"), ("interval", 10, "10 km w/ 3×1600m @ I-pace"),
     ("rest", 0, "Rest"), ("easy", 6, "Easy 6 km"), ("easy", 5, "Easy 5 km"),
     ("long", 16, "Long 16 km")],
    [("easy", 5, "Easy 5 km"), ("rest", 0, "Rest"), ("easy", 5, "Easy 5 km"),
     ("rest", 0, "Rest"), ("easy", 5, "Easy 5 km"), ("easy", 3, "Easy 3 km"),
     ("long", 10, "Long 10 km")],
    [("easy", 6, "Easy 6 km"), ("rest", 0, "Rest"), ("interval", 10, "10 km w/ 8×400m @ R-pace"),
     ("rest", 0, "Rest"), ("easy", 6, "Easy 6 km"), ("easy", 5, "Easy 5 km"),
     ("long", 14, "Long 14 km")],
    [("easy", 6, "Easy 6 km"), ("rest", 0, "Rest"), ("threshold", 8, "8 km w/ 4 km @ T-pace"),
     ("rest", 0, "Rest"), ("easy", 6, "Easy 6 km"), ("easy", 5, "Easy 5 km"),
     ("long", 13, "Long 13 km")],
    [("easy", 5, "Easy 5 km"), ("rest", 0, "Rest"), ("interval", 6, "6 km w/ 4×400m @ I-pace"),
     ("rest", 0, "Rest"), ("easy", 5, "Easy 5 km"), ("easy", 3, "Easy 3 km"),
     ("long", 10, "Long 10 km")],
    [("easy", 3, "Easy 3 km"), ("rest", 0, "Rest"), ("easy", 3, "Easy 3 km"),
     ("rest", 0, "Rest"), ("easy", 2, "Easy 2 km"), ("easy", 2, "Shakeout 2 km"),
     ("interval", 0, "Race day!")],
]

_TEMPLATES: dict[str, list] = {
    "marathon": _MARATHON_TEMPLATE_18W,
    "half":     _MARATHON_TEMPLATE_18W[:16],
    "10k":      _5K_TEMPLATE_12W,
    "5k":       _5K_TEMPLATE_12W,
}


def generate_daniels_plan(
    goal_distance: str,
    goal_race_date: date,
    target_vdot: float,
) -> list[dict[str, Any]]:
    """Generate a list of PlannedWorkout dicts for a Daniels plan."""
    template = _TEMPLATES.get(goal_distance, _MARATHON_TEMPLATE_18W)
    num_weeks = len(template)
    # Last workout is at offset (num_weeks-1)*7 + 6 from start; it should land on race day
    start_date = goal_race_date - timedelta(weeks=num_weeks - 1, days=6)
    paces = vdot_paces(target_vdot)

    workouts = []
    for week_idx, week_days in enumerate(template, start=1):
        for day_idx, (wtype, dist_km, desc) in enumerate(week_days):
            scheduled = start_date + timedelta(weeks=week_idx - 1, days=day_idx)
            target_dist = dist_km * 1000 if dist_km > 0 else None
            pace = paces.get(wtype) if wtype != "rest" else None
            workouts.append({
                "scheduled_date": scheduled,
                "week_number": week_idx,
                "workout_type": wtype,
                "description": desc,
                "target_distance_m": target_dist,
                "target_pace_s_per_km": pace,
            })
    return workouts
