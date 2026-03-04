from fastapi import APIRouter, Depends, BackgroundTasks
from sqlmodel import Session, select
from app.database import get_session
from app.models import Activity, DataPoint
from app.services.strava import sync_photos_for_activity
from app.services.coros import login as coros_login, list_activities as coros_list
from app.services.coros import download_fit, get_training_notes
from app.services.fit_parser import parse_fit_file
from app.config import COROS_EMAIL, COROS_PASSWORD, DATA_DIR
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/sync", tags=["sync"])
_last_sync: dict = {"status": "never", "ts": None, "error": None}


@router.get("/status")
def status():
    return _last_sync


@router.post("/trigger")
def trigger(bg: BackgroundTasks, session: Session = Depends(get_session)):
    bg.add_task(_sync_strava_photos, session)
    bg.add_task(_sync_coros, session)
    return {"message": "sync triggered"}


def _sync_strava_photos(session: Session):
    global _last_sync
    try:
        acts = session.exec(select(Activity).where(Activity.strava_id != None)).all()
        total = sum(sync_photos_for_activity(a, session) for a in acts)
        _last_sync = {"status": "ok", "ts": datetime.now(timezone.utc).isoformat(),
                      "new_photos": total, "error": None}
    except Exception as e:
        _last_sync = {"status": "error", "ts": datetime.now(timezone.utc).isoformat(),
                      "error": str(e)}


def _sync_coros(session: Session):
    global _last_sync
    if not COROS_EMAIL:
        return
    try:
        token = coros_login(COROS_EMAIL, COROS_PASSWORD)
        remote = coros_list(token)
        existing = {a.external_id for a in session.exec(select(Activity)).all()}
        new_count = 0
        for meta in remote:
            ext_id = str(meta.get("labelId", ""))
            if ext_id in existing:
                continue
            fit_bytes = download_fit(token, str(meta.get("sportType", "100")), ext_id)
            dest = DATA_DIR / f"{uuid.uuid4()}.fit"
            dest.write_bytes(fit_bytes)
            result = parse_fit_file(dest)
            notes = get_training_notes(token, ext_id)
            paces = [1000 / dp["speed_m_s"] for dp in result.datapoints
                     if dp.get("speed_m_s") and dp["speed_m_s"] > 0]
            act = Activity(
                source="coros", external_id=ext_id,
                started_at=result.started_at, distance_m=result.distance_m,
                duration_s=result.duration_s, elevation_gain_m=result.elevation_gain_m,
                avg_hr=result.avg_hr, sport_type=result.sport_type,
                fit_file_path=str(dest), notes=notes,
                avg_pace_s_per_km=sum(paces) / len(paces) if paces else None,
            )
            session.add(act)
            session.flush()
            for dp in result.datapoints:
                session.add(DataPoint(activity_id=act.id, **dp))
            new_count += 1
        session.commit()
        _last_sync = {"status": "ok", "ts": datetime.now(timezone.utc).isoformat(),
                      "new_activities": new_count, "error": None}
    except Exception as e:
        _last_sync = {"status": "error", "ts": datetime.now(timezone.utc).isoformat(),
                      "error": str(e)}
