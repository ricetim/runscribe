from fastapi import APIRouter, BackgroundTasks
from sqlmodel import Session, select
from app.database import engine
from app.models import Activity, DataPoint, Lap
from app.services.strava import sync_photos_for_activity
from app.services.coros import login as coros_login, list_activities as coros_list
from app.services.coros import download_fit, get_activity_detail
from app.services.fit_parser import parse_fit_file
from app.config import COROS_EMAIL, COROS_PASSWORD, DATA_DIR
from app.services.builder import bg_rebuild_all
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/sync", tags=["sync"])
_last_sync: dict = {"status": "never", "ts": None, "error": None}


@router.get("/status")
def status():
    return _last_sync


@router.post("/trigger")
def trigger(bg: BackgroundTasks):
    bg.add_task(_sync_strava_photos)
    bg.add_task(_sync_coros)
    return {"message": "sync triggered"}


def _sync_strava_photos() -> None:
    global _last_sync
    with Session(engine) as session:
        try:
            acts = session.exec(select(Activity).where(Activity.strava_id != None)).all()
            total = sum(sync_photos_for_activity(a, session) for a in acts)
            _last_sync = {"status": "ok", "ts": datetime.now(timezone.utc).isoformat(),
                          "new_photos": total, "error": None}
        except Exception as e:
            _last_sync = {"status": "error", "ts": datetime.now(timezone.utc).isoformat(),
                          "error": str(e)}


def _sync_coros() -> None:
    global _last_sync
    if not COROS_EMAIL:
        return
    with Session(engine) as session:
        try:
            token, user_id = coros_login(COROS_EMAIL, COROS_PASSWORD)
            remote = coros_list(token, user_id)
            existing_acts = {a.external_id: a for a in session.exec(select(Activity)).all()}
            new_count = 0
            for meta in remote:
                ext_id = str(meta.get("labelId", ""))
                sport_type_str = str(meta.get("sportType", "100"))
                activity_name = meta.get("name") or None
                if ext_id in existing_acts:
                    # Backfill name if missing
                    act = existing_acts[ext_id]
                    if act.name is None and activity_name:
                        act.name = activity_name
                        session.add(act)
                    continue
                fit_bytes = download_fit(token, user_id, ext_id, sport_type_str)
                dest = DATA_DIR / f"{uuid.uuid4()}.fit"
                dest.write_bytes(fit_bytes)
                result = parse_fit_file(dest)
                detail = get_activity_detail(token, user_id, ext_id, sport_type_str)
                avg_pace = result.duration_s / (result.distance_m / 1000) if result.distance_m > 0 else None
                act = Activity(
                    source="coros", external_id=ext_id,
                    started_at=result.started_at, distance_m=result.distance_m,
                    duration_s=result.duration_s, elevation_gain_m=result.elevation_gain_m,
                    elevation_loss_m=result.elevation_loss_m,
                    avg_hr=result.avg_hr, sport_type=result.sport_type,
                    fit_file_path=str(dest), notes=detail["notes"], rpe=detail["rpe"],
                    name=activity_name,
                    avg_pace_s_per_km=round(avg_pace, 1) if avg_pace else None,
                )
                session.add(act)
                session.flush()
                for dp in result.datapoints:
                    session.add(DataPoint(activity_id=act.id, **dp))
                for lap in result.laps:
                    session.add(Lap(
                        activity_id=act.id,
                        lap_number=lap.lap_number,
                        start_elapsed_s=lap.start_elapsed_s,
                        end_elapsed_s=lap.end_elapsed_s,
                        distance_m=lap.distance_m,
                        duration_s=lap.duration_s,
                        avg_hr=lap.avg_hr,
                        avg_pace_s_per_km=lap.avg_pace_s_per_km,
                        elevation_gain_m=lap.elevation_gain_m,
                    ))
                new_count += 1
            session.commit()
            _last_sync = {"status": "ok", "ts": datetime.now(timezone.utc).isoformat(),
                          "new_activities": new_count, "error": None}
            bg_rebuild_all()
        except Exception as e:
            _last_sync = {"status": "error", "ts": datetime.now(timezone.utc).isoformat(),
                          "error": str(e)}
