from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from app.database import get_session
from app.models import Goal, Activity

router = APIRouter(prefix="/api/goals", tags=["goals"])


def _progress_km(goal: Goal, session: Session) -> float:
    total = session.exec(
        select(func.sum(Activity.distance_m))
        .where(Activity.started_at >= goal.period_start)
        .where(Activity.started_at <= goal.period_end)
    ).first() or 0.0
    return round(total / 1000, 2)


@router.get("")
def list_goals(session: Session = Depends(get_session)):
    goals = session.exec(select(Goal)).all()
    return [{"goal": g.model_dump(), "progress_km": _progress_km(g, session)} for g in goals]


@router.post("", status_code=201)
def create_goal(goal: Goal, session: Session = Depends(get_session)):
    session.add(goal)
    session.commit()
    session.refresh(goal)
    return goal


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: int, session: Session = Depends(get_session)):
    goal = session.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404)
    session.delete(goal)
    session.commit()
