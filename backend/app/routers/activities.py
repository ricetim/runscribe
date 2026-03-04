import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlmodel import Session, select

from app.config import DATA_DIR
from app.database import get_session
from app.models import Activity, DataPoint, Photo
from app.services.fit_parser import parse_fit_file

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.get("", response_model=list[Activity])
def list_activities(session: Session = Depends(get_session)):
    return session.exec(select(Activity).order_by(Activity.started_at.desc())).all()


@router.get("/{activity_id}", response_model=Activity)
def get_activity(activity_id: int, session: Session = Depends(get_session)):
    act = session.get(Activity, activity_id)
    if not act:
        raise HTTPException(status_code=404, detail="Activity not found")
    return act


@router.get("/{activity_id}/datapoints")
def get_datapoints(activity_id: int, session: Session = Depends(get_session)):
    if not session.get(Activity, activity_id):
        raise HTTPException(status_code=404, detail="Activity not found")
    return session.exec(
        select(DataPoint)
        .where(DataPoint.activity_id == activity_id)
        .order_by(DataPoint.timestamp)
    ).all()


@router.get("/{activity_id}/photos")
def get_photos(activity_id: int, session: Session = Depends(get_session)):
    if not session.get(Activity, activity_id):
        raise HTTPException(status_code=404, detail="Activity not found")
    return session.exec(
        select(Photo).where(Photo.activity_id == activity_id)
    ).all()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_fit(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    dest = DATA_DIR / f"{uuid.uuid4()}.fit"
    with dest.open("wb") as buf:
        shutil.copyfileobj(file.file, buf)

    try:
        result = parse_fit_file(dest)
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Cannot parse FIT file: {e}")

    paces = [
        1000 / dp["speed_m_s"]
        for dp in result.datapoints
        if dp.get("speed_m_s") and dp["speed_m_s"] > 0
    ]
    act = Activity(
        source="manual_upload",
        started_at=result.started_at,
        distance_m=result.distance_m,
        duration_s=result.duration_s,
        elevation_gain_m=result.elevation_gain_m,
        avg_hr=result.avg_hr,
        sport_type=result.sport_type,
        fit_file_path=str(dest),
        avg_pace_s_per_km=sum(paces) / len(paces) if paces else None,
    )
    session.add(act)
    session.flush()

    for dp in result.datapoints:
        session.add(DataPoint(activity_id=act.id, **dp))

    session.commit()
    session.refresh(act)
    return act


@router.patch("/{activity_id}")
def update_activity(
    activity_id: int,
    data: dict,
    session: Session = Depends(get_session),
):
    act = session.get(Activity, activity_id)
    if not act:
        raise HTTPException(status_code=404, detail="Activity not found")
    for key in {"notes", "strava_id"}:
        if key in data:
            setattr(act, key, data[key])
    session.add(act)
    session.commit()
    session.refresh(act)
    return act
