from datetime import timedelta, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import Session, select, func
from app.database import get_session
from app.models import Goal, Activity
from app.services.builder import bg_rebuild_globals

router = APIRouter(prefix="/api/goals", tags=["goals"])


def _progress_km(goal: Goal, session: Session) -> float:
    total = session.exec(
        select(func.sum(Activity.distance_m))
        .where(Activity.started_at >= goal.period_start)
        .where(Activity.started_at < goal.period_end + timedelta(days=1))
    ).first() or 0.0
    return round(total / 1000, 2)


@router.get("")
def list_goals(session: Session = Depends(get_session)):
    goals = session.exec(select(Goal)).all()
    return [{"goal": g.model_dump(), "progress_km": _progress_km(g, session)} for g in goals]


class GoalCreate(BaseModel):
    type: str
    target_value: float
    period_start: date
    period_end: date
    notes: Optional[str] = None


@router.post("", status_code=201)
def create_goal(body: GoalCreate, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    goal = Goal(
        type=body.type,
        target_value=body.target_value,
        period_start=body.period_start,
        period_end=body.period_end,
        notes=body.notes,
    )
    session.add(goal)
    session.commit()
    session.refresh(goal)
    background_tasks.add_task(bg_rebuild_globals)
    return goal


@router.put("/{goal_id}")
def update_goal(goal_id: int, body: GoalCreate, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    goal = session.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404)
    goal.type = body.type
    goal.target_value = body.target_value
    goal.period_start = body.period_start
    goal.period_end = body.period_end
    goal.notes = body.notes
    session.commit()
    session.refresh(goal)
    background_tasks.add_task(bg_rebuild_globals)
    return {"goal": goal.model_dump(), "progress_km": _progress_km(goal, session)}


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: int, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    goal = session.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404)
    session.delete(goal)
    session.commit()
    background_tasks.add_task(bg_rebuild_globals)
