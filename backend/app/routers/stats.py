"""
Stats router: aggregate statistics, training load (ATL/CTL/TSB), VDOT,
pace zones, and per-activity analytics.
"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func

from app.database import get_session
from app.models import Activity, DataPoint, UserProfile
from app.services.analytics import (
    compute_vdot,
    compute_vdot_hr_adjusted,
    compute_pace_zones,
    compute_trimp,
    compute_hrtss,
    compute_training_loads,
    PaceZones,
    TrainingLoad,
)

router = APIRouter(prefix="/api/stats", tags=["stats"])


# ---------------------------------------------------------------------------
# Helper: build TSS-by-date dict from all activities in the DB
# ---------------------------------------------------------------------------

def _build_tss_by_date(session: Session) -> dict[date, float]:
    """Compute daily hrTSS for all activities using stored DataPoints."""
    profile = session.get(UserProfile, 1) or UserProfile()
    acts = session.exec(select(Activity).order_by(Activity.started_at)).all()
    tss_by_date: dict[date, float] = {}

    for act in acts:
        day = act.started_at.date()
        if act.avg_hr and act.duration_s:
            # Fast path: no datapoints needed — estimate from average HR
            hr_rest, hr_max = profile.hr_rest, profile.hr_max
            hr_range = hr_max - hr_rest
            delta_hr = max(0.0, min((act.avg_hr - hr_rest) / hr_range, 1.0))
            import math
            b = 1.92
            trimp = (act.duration_s / 60.0) * delta_hr * math.exp(b * delta_hr)
        else:
            # Fallback: rough estimate from duration only (assume easy effort)
            trimp = (act.duration_s / 60.0) * 0.3 * math.exp(1.92 * 0.3)
        tss_by_date[day] = tss_by_date.get(day, 0.0) + compute_hrtss(trimp)

    return tss_by_date


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary")
def get_summary(
    period: str = Query("week", pattern="^(week|month|year|all)$"),
    session: Session = Depends(get_session),
):
    """
    Aggregate run counts, distance, duration, elevation for a time period.
    period: 'week' | 'month' | 'year' | 'all'
    """
    today = date.today()
    if period == "week":
        since = today - timedelta(days=7)
    elif period == "month":
        since = today - timedelta(days=30)
    elif period == "year":
        since = today - timedelta(days=365)
    else:
        since = date(1970, 1, 1)

    acts = session.exec(
        select(Activity).where(Activity.started_at >= since.isoformat())
    ).all()

    total_km = sum(a.distance_m for a in acts) / 1000
    total_s = sum(a.duration_s for a in acts)
    total_elev = sum(a.elevation_gain_m for a in acts)
    count = len(acts)
    avg_pace = (sum(a.avg_pace_s_per_km for a in acts if a.avg_pace_s_per_km)
                / max(1, sum(1 for a in acts if a.avg_pace_s_per_km)))

    return {
        "period": period,
        "count": count,
        "total_distance_km": round(total_km, 2),
        "total_duration_s": total_s,
        "total_elevation_m": round(total_elev, 1),
        "avg_pace_s_per_km": round(avg_pace, 1) if avg_pace else None,
    }


@router.get("/training-load")
def get_training_load(
    days: int = Query(90, ge=7, le=365),
    session: Session = Depends(get_session),
):
    """
    Return daily ATL, CTL, TSB (training load) for the last `days` days.
    """
    tss_by_date = _build_tss_by_date(session)
    today = date.today()
    start = today - timedelta(days=days)
    loads = compute_training_loads(tss_by_date, start_date=start, end_date=today)

    return [
        {
            "date": d.isoformat(),
            "ctl": round(v.ctl, 1),
            "atl": round(v.atl, 1),
            "tsb": round(v.tsb, 1),
            "tss": round(tss_by_date.get(d, 0.0), 1),
        }
        for d, v in sorted(loads.items())
    ]


@router.get("/vdot")
def get_vdot(session: Session = Depends(get_session)):
    """
    Estimate current VDOT from recent training runs using HR-adjusted method.

    Uses Swain (1994) %VO2max = 1.0197×%HRR + 0.01 to account for the fact
    that training runs are run at sub-maximal effort. Takes the median of
    all qualifying activities in the last 90 days (requires avg_hr data).

    Falls back to the raw Daniels formula (best performance) only when no
    HR data is available — this will underestimate VDOT for easy runs.
    """
    profile = session.get(UserProfile, 1) or UserProfile()
    hr_max = profile.hr_max
    hr_rest = profile.hr_rest

    cutoff = date.today() - timedelta(days=28)
    acts = session.exec(
        select(Activity)
        .where(Activity.started_at >= cutoff.isoformat())
        .where(Activity.distance_m >= 3000)   # at least 3km for meaningful estimate
        .where(Activity.duration_s > 0)
    ).all()

    vdot_estimates = []
    for act in acts:
        if act.avg_hr and act.distance_m > 0 and act.duration_s > 0:
            try:
                v = compute_vdot_hr_adjusted(
                    act.distance_m, act.duration_s, act.avg_hr, hr_max, hr_rest
                )
                if 20 < v < 85:  # sanity range
                    vdot_estimates.append((v, act.id))
            except ValueError:
                pass

    method = "hr_adjusted"
    if vdot_estimates:
        # Use 75th percentile to reduce noise from unusually easy/hard days
        vdot_estimates.sort(key=lambda x: x[0])
        mid = int(len(vdot_estimates) * 0.75)
        mid = min(mid, len(vdot_estimates) - 1)
        best_vdot, best_act_id = vdot_estimates[mid]
    else:
        # Fallback: raw Daniels (accurate only for races/time-trials)
        method = "raw_daniels_fallback"
        best_vdot = None
        best_act_id = None
        for act in acts:
            if act.distance_m > 0 and act.duration_s > 0:
                try:
                    v = compute_vdot(act.distance_m, act.duration_s)
                    if best_vdot is None or v > best_vdot:
                        best_vdot = v
                        best_act_id = act.id
                except ValueError:
                    pass

    if best_vdot is None:
        return {"vdot": None, "based_on_activity_id": None, "method": method,
                "hr_max": hr_max, "hr_rest": hr_rest}

    zones = compute_pace_zones(best_vdot)
    from app.services.analytics import predict_race_time_s
    predictions = {}
    for name, dist in [("5k", 5000), ("10k", 10000), ("half", 21097), ("marathon", 42195)]:
        try:
            t = predict_race_time_s(best_vdot, dist)
            predictions[name] = round(t)
        except Exception:
            predictions[name] = None

    return {
        "vdot": round(best_vdot, 1),
        "based_on_activity_id": best_act_id,
        "method": method,
        "hr_max": hr_max,
        "hr_rest": hr_rest,
        "sample_size": len(vdot_estimates),
        "race_predictions_s": predictions,
        "pace_zones_s_per_km": {
            "easy_lo": round(zones.easy_lo),
            "easy_hi": round(zones.easy_hi),
            "marathon": round(zones.marathon),
            "threshold": round(zones.threshold),
            "interval": round(zones.interval),
            "repetition": round(zones.repetition),
        },
    }


@router.get("/personal-bests")
def get_personal_bests(session: Session = Depends(get_session)):
    """
    Best predicted race times for common distances (400 m → marathon).

    Finds the single best HR-adjusted VDOT across all activities (all-time,
    not windowed), then uses the Daniels prediction model to project times
    at each standard distance. This gives physiologically consistent
    predictions rather than naive pace × distance extrapolation.

    Returns null for all distances when no qualifying HR data exists.
    """
    from app.services.analytics import predict_race_time_s

    DISTANCES = [
        ("400m",     400),
        ("800m",     800),
        ("1 mile",   1609),
        ("5k",       5000),
        ("10k",      10000),
        ("half",     21097),
        ("marathon", 42195),
    ]

    profile = session.get(UserProfile, 1) or UserProfile()
    hr_max, hr_rest = profile.hr_max, profile.hr_rest

    acts = session.exec(
        select(Activity)
        .where(Activity.avg_hr.is_not(None))
        .where(Activity.distance_m >= 3000)
        .where(Activity.duration_s > 0)
    ).all()

    best_vdot: float | None = None
    for act in acts:
        if act.avg_hr and act.distance_m > 0 and act.duration_s > 0:
            try:
                v = compute_vdot_hr_adjusted(
                    act.distance_m, act.duration_s, act.avg_hr, hr_max, hr_rest
                )
                if 20 < v < 85 and (best_vdot is None or v > best_vdot):
                    best_vdot = v
            except ValueError:
                pass

    if best_vdot is None:
        return {label: None for label, _ in DISTANCES}

    results: dict[str, int | None] = {}
    for label, dist_m in DISTANCES:
        try:
            results[label] = round(predict_race_time_s(best_vdot, dist_m))
        except Exception:
            results[label] = None
    return results


@router.get("/activities/{activity_id}/analytics")
def get_activity_analytics(
    activity_id: int,
    hr_rest: int = Query(50, ge=30, le=100),
    hr_max: int = Query(190, ge=150, le=230),
    session: Session = Depends(get_session),
):
    """
    Per-activity analytics: VDOT estimate, TRIMP, hrTSS, pace zones,
    and grade-adjusted pace summary.
    """
    act = session.get(Activity, activity_id)
    if not act:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Activity not found")

    # VDOT
    vdot = None
    zones = None
    if act.distance_m >= 1000 and act.duration_s > 0:
        try:
            vdot = round(compute_vdot(act.distance_m, act.duration_s), 1)
            zones_obj = compute_pace_zones(vdot)
            zones = {
                "easy_lo": round(zones_obj.easy_lo),
                "easy_hi": round(zones_obj.easy_hi),
                "marathon": round(zones_obj.marathon),
                "threshold": round(zones_obj.threshold),
                "interval": round(zones_obj.interval),
                "repetition": round(zones_obj.repetition),
            }
        except ValueError:
            pass

    # TRIMP from datapoints
    dps = session.exec(
        select(DataPoint)
        .where(DataPoint.activity_id == activity_id)
        .order_by(DataPoint.timestamp)
    ).all()

    dp_dicts = [
        {"heart_rate": dp.heart_rate, "timestamp": dp.timestamp}
        for dp in dps
    ]
    trimp = round(compute_trimp(dp_dicts, hr_rest=hr_rest, hr_max=hr_max), 1)
    hrtss = round(compute_hrtss(trimp), 1)

    return {
        "activity_id": activity_id,
        "vdot": vdot,
        "trimp": trimp,
        "hrtss": hrtss,
        "pace_zones_s_per_km": zones,
    }
