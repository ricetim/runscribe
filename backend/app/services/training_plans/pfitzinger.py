"""
Pfitzinger 18-week marathon plan generator.
Structure based on the 18/55 plan from "Advanced Marathoning" (Pfitzinger & Douglas).
Distances scaled proportionally from the 55 mpw (88 km/wk) peak plan.
"""
from datetime import date, timedelta
from typing import Any

# Each week: list of (workout_type, distance_km, description)
# 0 km = rest/race day
_PFITZ_18_55 = [
    # Week 1 (base, ~64 km)
    [("recovery", 10, "Recovery 10 km"), ("rest", 0, "Rest"), ("easy", 13, "General aerobic 13 km"),
     ("rest", 0, "Rest"), ("easy", 11, "General aerobic 11 km"), ("easy", 8, "General aerobic 8 km"),
     ("long", 22, "Long run 22 km")],
    # Week 2 (~72 km)
    [("recovery", 10, "Recovery 10 km"), ("rest", 0, "Rest"), ("easy", 16, "General aerobic 16 km"),
     ("rest", 0, "Rest"), ("easy", 11, "General aerobic 11 km"), ("easy", 8, "General aerobic 8 km"),
     ("long", 27, "Long run 27 km")],
    # Week 3 (~80 km)
    [("recovery", 10, "Recovery 10 km"), ("rest", 0, "Rest"), ("marathon_pace", 16, "Med-long 16 km"),
     ("rest", 0, "Rest"), ("easy", 13, "General aerobic 13 km"), ("easy", 8, "General aerobic 8 km"),
     ("long", 29, "Long run 29 km")],
    # Week 4 — recovery (~55 km)
    [("recovery", 8, "Recovery 8 km"), ("rest", 0, "Rest"), ("easy", 11, "General aerobic 11 km"),
     ("rest", 0, "Rest"), ("easy", 10, "General aerobic 10 km"), ("easy", 8, "General aerobic 8 km"),
     ("long", 18, "Long run 18 km")],
    # Week 5 (~80 km)
    [("recovery", 10, "Recovery 10 km"), ("rest", 0, "Rest"), ("threshold", 16, "LT 16 km w/ 8 km @ LT"),
     ("rest", 0, "Rest"), ("easy", 13, "General aerobic 13 km"), ("easy", 8, "General aerobic 8 km"),
     ("long", 29, "Long run 29 km")],
    # Week 6 (~88 km — peak week 1)
    [("recovery", 10, "Recovery 10 km"), ("rest", 0, "Rest"), ("marathon_pace", 19, "Med-long 19 km"),
     ("rest", 0, "Rest"), ("easy", 13, "General aerobic 13 km"), ("easy", 8, "General aerobic 8 km"),
     ("long", 32, "Long run 32 km")],
    # Week 7 (~88 km — peak week 2)
    [("recovery", 10, "Recovery 10 km"), ("rest", 0, "Rest"), ("threshold", 16, "LT 16 km w/ 10 km @ LT"),
     ("rest", 0, "Rest"), ("easy", 13, "General aerobic 13 km"), ("easy", 8, "General aerobic 8 km"),
     ("long", 35, "Long run 35 km")],
    # Week 8 — recovery (~56 km)
    [("recovery", 8, "Recovery 8 km"), ("rest", 0, "Rest"), ("easy", 11, "General aerobic 11 km"),
     ("rest", 0, "Rest"), ("easy", 10, "General aerobic 10 km"), ("easy", 8, "General aerobic 8 km"),
     ("long", 19, "Long run 19 km")],
    # Week 9 (~88 km — peak week 3)
    [("recovery", 10, "Recovery 10 km"), ("rest", 0, "Rest"), ("marathon_pace", 19, "Med-long 19 km"),
     ("rest", 0, "Rest"), ("easy", 13, "General aerobic 13 km"), ("easy", 8, "General aerobic 8 km"),
     ("long", 32, "Long run 32 km")],
    # Week 10 (~88 km — peak week 4)
    [("recovery", 10, "Recovery 10 km"), ("rest", 0, "Rest"), ("threshold", 16, "LT 16 km w/ 11 km @ LT"),
     ("rest", 0, "Rest"), ("easy", 13, "General aerobic 13 km"), ("easy", 8, "General aerobic 8 km"),
     ("long", 35, "Long run 35 km")],
    # Week 11 (~88 km — peak week 5)
    [("recovery", 10, "Recovery 10 km"), ("rest", 0, "Rest"), ("marathon_pace", 21, "Med-long 21 km"),
     ("rest", 0, "Rest"), ("easy", 13, "General aerobic 13 km"), ("easy", 8, "General aerobic 8 km"),
     ("long", 32, "Long run 32 km")],
    # Week 12 — recovery (~56 km)
    [("recovery", 8, "Recovery 8 km"), ("rest", 0, "Rest"), ("easy", 11, "General aerobic 11 km"),
     ("rest", 0, "Rest"), ("easy", 10, "General aerobic 10 km"), ("easy", 8, "General aerobic 8 km"),
     ("long", 19, "Long run 19 km")],
    # Week 13 (~80 km)
    [("recovery", 10, "Recovery 10 km"), ("rest", 0, "Rest"), ("marathon_pace", 19, "Med-long 19 km w/ 13 @ MP"),
     ("rest", 0, "Rest"), ("easy", 13, "General aerobic 13 km"), ("easy", 8, "General aerobic 8 km"),
     ("long", 29, "Long run 29 km")],
    # Week 14 (~80 km)
    [("recovery", 10, "Recovery 10 km"), ("rest", 0, "Rest"), ("threshold", 16, "LT 16 km w/ 10 km @ LT"),
     ("rest", 0, "Rest"), ("easy", 13, "General aerobic 13 km"), ("easy", 8, "General aerobic 8 km"),
     ("long", 29, "Long run 29 km")],
    # Week 15 (~72 km — begin taper)
    [("recovery", 8, "Recovery 8 km"), ("rest", 0, "Rest"), ("marathon_pace", 16, "Med-long 16 km w/ 10 @ MP"),
     ("rest", 0, "Rest"), ("easy", 11, "General aerobic 11 km"), ("easy", 8, "General aerobic 8 km"),
     ("long", 24, "Long run 24 km")],
    # Week 16 (~56 km — taper continues)
    [("recovery", 8, "Recovery 8 km"), ("rest", 0, "Rest"), ("easy", 13, "General aerobic 13 km"),
     ("rest", 0, "Rest"), ("easy", 10, "General aerobic 10 km"), ("easy", 6, "General aerobic 6 km"),
     ("long", 19, "Long run 19 km")],
    # Week 17 (~40 km — heavy taper)
    [("recovery", 6, "Recovery 6 km"), ("rest", 0, "Rest"), ("marathon_pace", 11, "11 km w/ 6 @ MP"),
     ("rest", 0, "Rest"), ("easy", 8, "General aerobic 8 km"), ("easy", 5, "General aerobic 5 km"),
     ("long", 16, "Long run 16 km")],
    # Week 18 — race week (~26 km + race)
    [("recovery", 6, "Recovery 6 km"), ("rest", 0, "Rest"), ("easy", 8, "Easy 8 km"),
     ("rest", 0, "Rest"), ("easy", 5, "Easy 5 km"), ("easy", 3, "Shakeout 3 km"),
     ("marathon_pace", 0, "Race day — Marathon!")],
]


def generate_pfitzinger_plan(
    goal_race_date: date,
    peak_weekly_km: float = 88.0,
) -> list[dict[str, Any]]:
    """
    Generate Pfitzinger 18-week marathon plan.
    Scales distances proportionally from the 88 km/week peak template.
    """
    scale = peak_weekly_km / 88.0
    num_weeks = len(_PFITZ_18_55)
    start_date = goal_race_date - timedelta(weeks=num_weeks)

    workouts = []
    for week_idx, week_days in enumerate(_PFITZ_18_55, start=1):
        for day_idx, (wtype, dist_km, desc) in enumerate(week_days):
            scheduled = start_date + timedelta(weeks=week_idx - 1, days=day_idx)
            scaled_km = dist_km * scale
            target_dist = scaled_km * 1000 if scaled_km > 0 else None
            workouts.append({
                "scheduled_date": scheduled,
                "week_number": week_idx,
                "workout_type": wtype,
                "description": desc,
                "target_distance_m": target_dist,
                "target_pace_s_per_km": None,  # Pfitzinger paces set by feel/LT test
            })
    return workouts
