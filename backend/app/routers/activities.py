import shutil
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import DATA_DIR
from app.database import get_session
from app.models import Activity, DataPoint, Photo, PlannedWorkout
from app.services.fit_parser import parse_fit_file

router = APIRouter(prefix="/api/activities", tags=["activities"])


class ActivitySummary(BaseModel):
    id: int
    source: str
    external_id: Optional[str] = None
    strava_id: Optional[str] = None
    started_at: datetime
    distance_m: float
    duration_s: int
    elevation_gain_m: float
    avg_hr: Optional[int] = None
    avg_pace_s_per_km: Optional[float] = None
    sport_type: str
    notes: Optional[str] = None
    rpe: Optional[int] = None
    track: list[list[float]] = []
    planned_workout_type: Optional[str] = None


def _downsample(points: list[list[float]], max_points: int = 150) -> list[list[float]]:
    if len(points) <= max_points:
        return points
    step = len(points) / max_points
    indices = {0, len(points) - 1}
    indices.update(int(i * step) for i in range(1, max_points - 1))
    return [points[i] for i in sorted(indices)]


@router.get("", response_model=list[ActivitySummary])
def list_activities(session: Session = Depends(get_session)):
    activities = session.exec(
        select(Activity).order_by(Activity.started_at.desc())
    ).all()

    if not activities:
        return []

    activity_ids = [a.id for a in activities]

    # Bulk fetch only lat/lon for all activities (avoids N+1)
    gps_rows = session.exec(
        select(DataPoint.activity_id, DataPoint.lat, DataPoint.lon)
        .where(DataPoint.activity_id.in_(activity_ids))
        .where(DataPoint.lat.is_not(None))
        .where(DataPoint.lon.is_not(None))
        .order_by(DataPoint.activity_id, DataPoint.timestamp)
    ).all()

    gps_by_activity: dict[int, list[list[float]]] = defaultdict(list)
    for row in gps_rows:
        gps_by_activity[row[0]].append([row[1], row[2]])

    # Bulk fetch planned workout types linked to these activities
    planned_rows = session.exec(
        select(PlannedWorkout.completed_activity_id, PlannedWorkout.workout_type)
        .where(PlannedWorkout.completed_activity_id.in_(activity_ids))
    ).all()
    planned_type_by_activity = {row[0]: row[1] for row in planned_rows}

    return [
        ActivitySummary(
            id=a.id,
            source=a.source,
            external_id=a.external_id,
            strava_id=a.strava_id,
            started_at=a.started_at,
            distance_m=a.distance_m,
            duration_s=a.duration_s,
            elevation_gain_m=a.elevation_gain_m,
            avg_hr=a.avg_hr,
            avg_pace_s_per_km=a.avg_pace_s_per_km,
            sport_type=a.sport_type,
            notes=a.notes,
            rpe=a.rpe,
            track=_downsample(gps_by_activity.get(a.id, [])),
            planned_workout_type=planned_type_by_activity.get(a.id),
        )
        for a in activities
    ]


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
    for key in {"notes", "strava_id", "rpe"}:
        if key in data:
            setattr(act, key, data[key])
    session.add(act)
    session.commit()
    session.refresh(act)
    return act
