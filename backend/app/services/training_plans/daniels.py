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


# ── Daniels phase plan templates (4 weeks each) ────────────────────────────
# Each phase is a standalone 4-week training block following the 2Q structure
# from Daniels' Running Formula (4th ed., 2022), Chapter 8.
#
# Every week has exactly 2 Q (quality) days and the remainder are E (easy) or rest.
# Format per day: (workout_type, distance_km, description, optional)
#   optional=True days are bonus easy runs — safe to skip if recovering.
#
# Days: Mon(0) Tue(1) Wed(2) Thu(3) Fri(4) Sat(5) Sun(6)
# Layout: E  Q1  E  Q2  E  E  L
# Q1 is the primary quality session; Q2 is the secondary quality session.
# L (long run) is always easy pace and is NOT a Q day.

# WHITE — Phase I: Foundation. Q days are medium-long E runs with strides.
# Purpose: establish aerobic base, neuromuscular efficiency via strides,
# no anaerobic stress.
_WHITE_PLAN = [
    # Week 1 (~50 km)
    [("easy",   6,  "E 6 km",                                False),
     ("easy",  10,  "Q1: E 10 km + 6×20 s strides (2 min E after each)", False),  # Q1
     ("easy",   6,  "E 6 km",                                False),
     ("easy",   8,  "Q2: E 8 km + 6×20 s strides",          False),  # Q2
     ("easy",   5,  "E 5 km (optional)",                     True),
     ("easy",   5,  "E 5 km",                                False),
     ("long",  14,  "L 14 km easy",                          False)],
    # Week 2 (~58 km)
    [("easy",   6,  "E 6 km",                                False),
     ("easy",  13,  "Q1: E 13 km + 6×20 s strides",         False),  # Q1
     ("easy",   6,  "E 6 km",                                False),
     ("easy",  10,  "Q2: E 10 km + 8×20 s strides",         False),  # Q2
     ("easy",   5,  "E 5 km (optional)",                     True),
     ("easy",   5,  "E 5 km",                                False),
     ("long",  16,  "L 16 km easy",                          False)],
    # Week 3 (~64 km)
    [("easy",   6,  "E 6 km",                                False),
     ("easy",  16,  "Q1: E 16 km + 8×20 s strides",         False),  # Q1
     ("easy",   6,  "E 6 km",                                False),
     ("easy",  11,  "Q2: E 11 km + 8×20 s strides",         False),  # Q2
     ("easy",   5,  "E 5 km (optional)",                     True),
     ("easy",   5,  "E 5 km",                                False),
     ("long",  19,  "L 19 km easy",                          False)],
    # Week 4 — recovery (~46 km)
    [("easy",   5,  "E 5 km",                                False),
     ("easy",   8,  "Q1: E 8 km + 4×20 s strides",          False),  # Q1
     ("easy",   5,  "E 5 km",                                False),
     ("easy",   6,  "Q2: E 6 km + 4×20 s strides",          False),  # Q2
     ("rest",   0,  "Rest",                                   False),
     ("easy",   5,  "E 5 km",                                False),
     ("long",  13,  "L 13 km easy",                          False)],
]

# RED — Phase II: R-pace. Q1 = Repetition (R), Q2 = Threshold (T cruise intervals).
# Purpose: develop speed, economy, and lactate clearance via R-pace reps;
# introduce T-pace for lactate threshold development.
_RED_PLAN = [
    # Week 1 (~55 km)
    [("easy",   6,  "E 6 km",                                False),
     ("repetition", 9,
      "Q1: 2 km E + 5×400 m @R (400 m jog) + 2 km E",       False),  # Q1
     ("easy",   6,  "E 6 km",                                False),
     ("threshold",  8,
      "Q2: 2 km E + 4×1 km @T (1 min rest) + 2 km E",       False),  # Q2
     ("easy",   5,  "E 5 km (optional)",                     True),
     ("easy",   5,  "E 5 km",                                False),
     ("long",  16,  "L 16 km easy",                          False)],
    # Week 2 (~58 km)
    [("easy",   6,  "E 6 km",                                False),
     ("repetition", 10,
      "Q1: 2 km E + 6×400 m @R (400 m jog) + 4×200 m @R (200 m jog) + 2 km E", False),
     ("easy",   6,  "E 6 km",                                False),
     ("threshold",  9,
      "Q2: 2 km E + 5×1 km @T (1 min rest) + 2 km E",       False),  # Q2
     ("easy",   5,  "E 5 km (optional)",                     True),
     ("easy",   5,  "E 5 km",                                False),
     ("long",  18,  "L 18 km easy",                          False)],
    # Week 3 (~62 km)
    [("easy",   8,  "E 8 km",                                False),
     ("repetition", 11,
      "Q1: 2 km E + 3×800 m @R (800 m jog) + 4×400 m @R (400 m jog) + 2 km E", False),
     ("easy",   6,  "E 6 km",                                False),
     ("threshold", 10,
      "Q2: 2 km E + 20 min @T continuous + 2 km E",          False),  # Q2
     ("easy",   5,  "E 5 km (optional)",                     True),
     ("easy",   5,  "E 5 km",                                False),
     ("long",  19,  "L 19 km easy",                          False)],
    # Week 4 — recovery (~46 km)
    [("easy",   5,  "E 5 km",                                False),
     ("repetition",  7,
      "Q1: 2 km E + 4×400 m @R (400 m jog) + 2 km E",       False),  # Q1
     ("easy",   5,  "E 5 km",                                False),
     ("threshold",  7,
      "Q2: 2 km E + 3×1 km @T (1 min rest) + 2 km E",       False),  # Q2
     ("rest",   0,  "Rest",                                   False),
     ("easy",   5,  "E 5 km",                                False),
     ("long",  14,  "L 14 km easy",                          False)],
]

# BLUE — Phase III: I-pace. Q1 = Interval (I), Q2 = Threshold (T longer).
# Purpose: develop VO2max via I-pace work; extend T-pace volume.
_BLUE_PLAN = [
    # Week 1 (~60 km)
    [("easy",   8,  "E 8 km",                                False),
     ("interval", 11,
      "Q1: 2 km E + 4×1200 m @I (3 min jog) + 1 km E",      False),  # Q1
     ("easy",   6,  "E 6 km",                                False),
     ("threshold", 10,
      "Q2: 2 km E + 5×1 km @T (1 min rest) + 2 km E",       False),  # Q2
     ("easy",   5,  "E 5 km (optional)",                     True),
     ("easy",   5,  "E 5 km",                                False),
     ("long",  19,  "L 19 km easy",                          False)],
    # Week 2 (~65 km)
    [("easy",   8,  "E 8 km",                                False),
     ("interval", 12,
      "Q1: 2 km E + 5×1200 m @I (3 min jog) + 1 km E",      False),  # Q1
     ("easy",   6,  "E 6 km",                                False),
     ("threshold", 11,
      "Q2: 2 km E + 6×1 km @T (1 min rest) + 2 km E",       False),  # Q2
     ("easy",   5,  "E 5 km (optional)",                     True),
     ("easy",   5,  "E 5 km",                                False),
     ("long",  21,  "L 21 km easy",                          False)],
    # Week 3 (~68 km)
    [("easy",   8,  "E 8 km",                                False),
     ("interval", 12,
      "Q1: 2 km E + 3×1600 m @I (400 m jog) + 1 km E",      False),  # Q1
     ("easy",   6,  "E 6 km",                                False),
     ("threshold", 12,
      "Q2: 2 km E + 25 min @T continuous + 2 km E",          False),  # Q2
     ("easy",   5,  "E 5 km (optional)",                     True),
     ("easy",   5,  "E 5 km",                                False),
     ("long",  22,  "L 22 km easy",                          False)],
    # Week 4 — recovery (~50 km)
    [("easy",   6,  "E 6 km",                                False),
     ("interval",  9,
      "Q1: 2 km E + 3×1200 m @I (3 min jog) + 1 km E",      False),  # Q1
     ("easy",   5,  "E 5 km",                                False),
     ("threshold",  8,
      "Q2: 2 km E + 3×1 km @T (1 min rest) + 2 km E",       False),  # Q2
     ("rest",   0,  "Rest",                                   False),
     ("easy",   5,  "E 5 km",                                False),
     ("long",  16,  "L 16 km easy",                          False)],
]

# GOLD — Phase IV: Peak / T-pace. Both Q days are hard.
# Q1 = Interval (I) work; Q2 = long Threshold (T) or combined I+T.
# Purpose: final quality sharpening; taper in week 4.
_GOLD_PLAN = [
    # Week 1 (~68 km)
    [("easy",   8,  "E 8 km",                                False),
     ("interval", 13,
      "Q1: 2 km E + 5×1000 m @I (200 m jog) + 2 km T + 1 km E", False),  # Q1
     ("easy",   6,  "E 6 km",                                False),
     ("threshold", 12,
      "Q2: 2 km E + 30 min @T continuous + 2 km E",          False),  # Q2
     ("easy",   5,  "E 5 km (optional)",                     True),
     ("easy",   5,  "E 5 km",                                False),
     ("long",  22,  "L 22 km easy",                          False)],
    # Week 2 (~72 km)
    [("easy",   8,  "E 8 km",                                False),
     ("interval", 14,
      "Q1: 2 km E + 3×1600 m @I (400 m jog) + 2 km T + 1 km E", False),  # Q1
     ("easy",   6,  "E 6 km",                                False),
     ("threshold", 13,
      "Q2: 2 km E + 35 min @T continuous + 2 km E",          False),  # Q2
     ("easy",   5,  "E 5 km (optional)",                     True),
     ("easy",   5,  "E 5 km",                                False),
     ("long",  24,  "L 24 km easy",                          False)],
    # Week 3 (~68 km)
    [("easy",   8,  "E 8 km",                                False),
     ("interval", 13,
      "Q1: 2 km E + 5×1200 m @I (3 min jog) + 2 km T + 1 km E", False),  # Q1
     ("easy",   6,  "E 6 km",                                False),
     ("threshold", 11,
      "Q2: 2 km E + 30 min @T continuous + 2 km E",          False),  # Q2
     ("easy",   5,  "E 5 km (optional)",                     True),
     ("easy",   5,  "E 5 km",                                False),
     ("long",  22,  "L 22 km easy",                          False)],
    # Week 4 — taper (~48 km)
    [("easy",   6,  "E 6 km",                                False),
     ("interval",  9,
      "Q1: 2 km E + 3×1000 m @I (200 m jog) + 1 km T + 1 km E", False),  # Q1
     ("easy",   5,  "E 5 km",                                False),
     ("threshold",  8,
      "Q2: 2 km E + 20 min @T continuous + 2 km E",          False),  # Q2
     ("rest",   0,  "Rest",                                   False),
     ("easy",   3,  "E 3 km shakeout",                       False),
     ("long",  13,  "L 13 km easy",                          False)],
]


_PHASE_PLANS: dict[str, list] = {
    "white": _WHITE_PLAN,
    "red":   _RED_PLAN,
    "blue":  _BLUE_PLAN,
    "gold":  _GOLD_PLAN,
}


def generate_daniels_phase_plan(
    phase: str,
    target_vdot: float,
    start_date: date | None = None,
) -> list[dict[str, Any]]:
    """
    Generate a 4-week Daniels phase training block (white/red/blue/gold).

    Only input required is the target VDOT; start_date defaults to the
    next Monday on or after today if not provided.

    White: Foundation — easy mileage and strides
    Red:   Early quality — R-pace repetitions and T-pace cruise intervals
    Blue:  Interval quality — I-pace work alongside T-pace
    Gold:  Peak quality — combined I+T sessions with taper

    Args:
        phase:        "white" | "red" | "blue" | "gold"
        target_vdot:  runner's VDOT for pace zone calculations
        start_date:   first Monday of the plan (defaults to next Monday)
    """
    template = _PHASE_PLANS.get(phase)
    if template is None:
        raise ValueError(f"Unknown Daniels phase: {phase!r}. Use white/red/blue/gold.")

    if start_date is None:
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7  # 0 if today is Monday
        start_date = today + timedelta(days=days_until_monday)

    paces = vdot_paces(target_vdot)
    workouts = []
    for week_idx, week_days in enumerate(template, start=1):
        for day_idx, (wtype, dist_km, desc, optional) in enumerate(week_days):
            scheduled = start_date + timedelta(weeks=week_idx - 1, days=day_idx)
            target_dist = dist_km * 1000 if dist_km > 0 else None
            # Only assign a target pace for actual quality workout types
            pace = paces.get(wtype) if wtype in ("repetition", "threshold", "interval", "marathon") else None
            workouts.append({
                "scheduled_date": scheduled,
                "week_number": week_idx,
                "workout_type": wtype,
                "description": desc,
                "target_distance_m": target_dist,
                "target_pace_s_per_km": pace,
                "optional": optional,
            })
    return workouts


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
