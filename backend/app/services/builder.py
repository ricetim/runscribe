"""
Static JSON snapshot builder.

After every write (upload, delete, goal, shoe, plan), the relevant
snapshot files in STATIC_DIR are regenerated atomically. nginx serves
these files directly, so reads never touch Python.
"""
import json
import math
import os
from collections import defaultdict
from datetime import date, timedelta, datetime
from pathlib import Path

import httpx
from sqlmodel import Session, select, func

STATIC_DIR = Path(os.environ.get("DATA_DIR", "/data")) / "static"
TILE_DIR = Path(os.environ.get("DATA_DIR", "/data")) / "tiles"

PROVIDERS = {
    "light":    "https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
    "standard": "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
    "dark":     "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
}
_TILE_HEADERS = {
    "User-Agent": "RunScribe/1.0 (tile pre-fetcher)",
    "Accept": "image/png,image/*",
}
_PREFETCH_ZOOMS = range(12, 15)  # zooms 12-14; ~20-50 tiles per activity


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _json_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Not JSON serializable: {type(obj)}")


def _write_json(path: Path, data) -> None:
    """Atomic write: write to .tmp, then os.replace so nginx never serves partial."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, default=_json_default))
    tmp.replace(path)


def _downsample(points: list, max_points: int = 150) -> list:
    if len(points) <= max_points:
        return points
    step = len(points) / max_points
    indices = {0, len(points) - 1}
    indices.update(int(i * step) for i in range(1, max_points - 1))
    return [points[i] for i in sorted(indices)]


def _tile_xy(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Convert lat/lon to OSM tile coordinates at the given zoom level."""
    lat_r = math.radians(lat)
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n)
    return x, y


# ---------------------------------------------------------------------------
# Per-activity rebuild
# ---------------------------------------------------------------------------

def rebuild_activity(
    activity_id: int,
    session: Session,
    static_dir: Path = STATIC_DIR,
    tile_dir: Path = TILE_DIR,
) -> None:
    """Write activity-{id}.json, datapoints-{id}.json, and pre-fetch map tiles."""
    from app.models import Activity, DataPoint, Lap

    act = session.get(Activity, activity_id)
    if not act:
        return

    laps = session.exec(
        select(Lap).where(Lap.activity_id == activity_id).order_by(Lap.lap_number)
    ).all()

    dps = session.exec(
        select(DataPoint)
        .where(DataPoint.activity_id == activity_id)
        .order_by(DataPoint.timestamp)
    ).all()

    gps_rows = [(dp.lat, dp.lon, dp.speed_m_s) for dp in dps if dp.lat and dp.lon]
    track = [[lat, lon, spd] for lat, lon, spd in gps_rows]

    _write_json(static_dir / f"activity-{activity_id}.json", {
        "activity": act.model_dump(),
        "laps": [lap.model_dump() for lap in laps],
        "track": track,
    })
    _write_json(static_dir / f"datapoints-{activity_id}.json", [dp.model_dump() for dp in dps])

    if gps_rows:
        _prefetch_tiles(gps_rows, tile_dir)


def _prefetch_tiles(gps_rows: list, tile_dir: Path) -> None:
    """Best-effort: fetch and cache map tiles for a GPS track's bounding box."""
    lats = [r[0] for r in gps_rows]
    lons = [r[1] for r in gps_rows]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    try:
        with httpx.Client(timeout=8) as client:
            for zoom in _PREFETCH_ZOOMS:
                x_min, y_max = _tile_xy(min_lat, min_lon, zoom)
                x_max, y_min = _tile_xy(max_lat, max_lon, zoom)
                for x in range(x_min, x_max + 1):
                    for y in range(y_min, y_max + 1):
                        for provider, url_tpl in PROVIDERS.items():
                            cache_path = tile_dir / provider / str(zoom) / str(x) / f"{y}.png"
                            if cache_path.exists():
                                continue
                            try:
                                resp = client.get(url_tpl.format(z=zoom, x=x, y=y), headers=_TILE_HEADERS)
                                if resp.status_code == 200:
                                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                                    cache_path.write_bytes(resp.content)
                            except httpx.RequestError:
                                pass
    except Exception:
        pass  # tile pre-fetch is best-effort; never block a rebuild


# ---------------------------------------------------------------------------
# Global files rebuild
# ---------------------------------------------------------------------------

def rebuild_globals(session: Session, static_dir: Path = STATIC_DIR) -> None:
    """Rebuild activities.json, dashboard.json, goals.json, shoes.json, plans.json."""
    _rebuild_activities(session, static_dir)
    _rebuild_dashboard(session, static_dir)
    _rebuild_goals(session, static_dir)
    _rebuild_shoes(session, static_dir)
    _rebuild_plans(session, static_dir)


def _rebuild_activities(session: Session, static_dir: Path) -> None:
    from app.models import Activity, DataPoint, PlannedWorkout

    activities = session.exec(select(Activity).order_by(Activity.started_at.desc())).all()
    if not activities:
        _write_json(static_dir / "activities.json", [])
        return

    ids = [a.id for a in activities]

    gps_rows = session.exec(
        select(DataPoint.activity_id, DataPoint.lat, DataPoint.lon)
        .where(DataPoint.activity_id.in_(ids))
        .where(DataPoint.lat.is_not(None))
        .where(DataPoint.lon.is_not(None))
        .order_by(DataPoint.activity_id, DataPoint.timestamp)
    ).all()
    gps_by_id: dict[int, list] = defaultdict(list)
    for row in gps_rows:
        gps_by_id[row[0]].append([row[1], row[2]])

    planned = session.exec(
        select(PlannedWorkout.completed_activity_id, PlannedWorkout.workout_type)
        .where(PlannedWorkout.completed_activity_id.in_(ids))
    ).all()
    plan_type = {row[0]: row[1] for row in planned}

    result = []
    for a in activities:
        d = a.model_dump()
        d["track"] = _downsample(gps_by_id.get(a.id, []))
        d["planned_workout_type"] = plan_type.get(a.id)
        result.append(d)

    _write_json(static_dir / "activities.json", result)


def _rebuild_dashboard(session: Session, static_dir: Path) -> None:
    from app.routers.stats import get_summary, get_training_load, get_vdot, get_personal_bests

    _write_json(static_dir / "dashboard.json", {
        "summary": {p: get_summary(period=p, session=session) for p in ("week", "month", "year", "all")},
        "training_load": get_training_load(days=365, session=session),
        "vdot": get_vdot(session=session),
        "personal_bests": get_personal_bests(session=session),
    })


def _rebuild_goals(session: Session, static_dir: Path) -> None:
    from app.models import Activity, Goal

    goals = session.exec(select(Goal)).all()
    result = []
    for g in goals:
        total = session.exec(
            select(func.sum(Activity.distance_m))
            .where(Activity.started_at >= g.period_start)
            .where(Activity.started_at < g.period_end + timedelta(days=1))
        ).first() or 0.0
        result.append({"goal": g.model_dump(), "progress_km": round(total / 1000, 2)})
    _write_json(static_dir / "goals.json", result)


def _rebuild_shoes(session: Session, static_dir: Path) -> None:
    from app.models import Activity, ActivityShoe, Shoe

    shoes = session.exec(select(Shoe)).all()
    result = []
    for shoe in shoes:
        dist = session.exec(
            select(func.sum(Activity.distance_m))
            .join(ActivityShoe, ActivityShoe.activity_id == Activity.id)
            .where(ActivityShoe.shoe_id == shoe.id)
        ).first() or 0.0
        result.append({**shoe.model_dump(), "total_distance_km": round(dist / 1000, 1)})
    _write_json(static_dir / "shoes.json", result)


def _rebuild_plans(session: Session, static_dir: Path) -> None:
    from app.models import PlannedWorkout, TrainingPlan

    plans = session.exec(select(TrainingPlan)).all()
    _write_json(static_dir / "plans.json", [p.model_dump() for p in plans])

    today = date.today()
    for plan in plans:
        workouts = session.exec(
            select(PlannedWorkout)
            .where(PlannedWorkout.training_plan_id == plan.id)
            .order_by(PlannedWorkout.scheduled_date)
        ).all()
        workout_list = []
        for w in workouts:
            if w.completed_activity_id:
                status = "completed"
            elif w.workout_type == "rest":
                status = "rest"
            elif w.scheduled_date < today:
                status = "missed"
            elif w.scheduled_date == today:
                status = "today"
            else:
                status = "future"
            workout_list.append({**w.model_dump(), "status": status})
        _write_json(static_dir / f"plan-{plan.id}.json", {
            "plan": plan.model_dump(),
            "workouts": workout_list,
        })


# ---------------------------------------------------------------------------
# Full rebuild
# ---------------------------------------------------------------------------

def rebuild_all(
    session: Session,
    static_dir: Path = STATIC_DIR,
    tile_dir: Path = TILE_DIR,
) -> None:
    """Rebuild every static file. Called on first startup or after Coros sync."""
    from app.models import Activity
    rebuild_globals(session, static_dir)
    for act in session.exec(select(Activity)).all():
        rebuild_activity(act.id, session, static_dir, tile_dir)


# ---------------------------------------------------------------------------
# Background-task-safe wrappers (open their own sessions)
# ---------------------------------------------------------------------------

def _new_session():
    from app.database import Session as _Session, engine
    return _Session(engine)


def bg_rebuild_after_upload(activity_id: int) -> None:
    """Call after a new activity is added."""
    try:
        with _new_session() as session:
            rebuild_activity(activity_id, session)
            rebuild_globals(session)
    except Exception as exc:
        print(f"[builder] bg_rebuild_after_upload failed: {exc}")


def bg_rebuild_after_delete(activity_id: int, static_dir: Path = STATIC_DIR) -> None:
    """Call after an activity is deleted. Removes per-activity files, rebuilds globals."""
    try:
        for name in (f"activity-{activity_id}.json", f"datapoints-{activity_id}.json"):
            (static_dir / name).unlink(missing_ok=True)
        with _new_session() as session:
            rebuild_globals(session, static_dir)
    except Exception as exc:
        print(f"[builder] bg_rebuild_after_delete failed: {exc}")


def bg_rebuild_after_activity_update(activity_id: int) -> None:
    """Call after notes/rpe/strava_id updated."""
    try:
        with _new_session() as session:
            rebuild_activity(activity_id, session)
            _rebuild_activities(session, STATIC_DIR)
    except Exception as exc:
        print(f"[builder] bg_rebuild_after_activity_update failed: {exc}")


def bg_rebuild_globals() -> None:
    """Call after goal/shoe/plan changes."""
    try:
        with _new_session() as session:
            rebuild_globals(session)
    except Exception as exc:
        print(f"[builder] bg_rebuild_globals failed: {exc}")


def bg_rebuild_all() -> None:
    """Call after Coros sync completes."""
    try:
        with _new_session() as session:
            rebuild_all(session)
    except Exception as exc:
        print(f"[builder] bg_rebuild_all failed: {exc}")
