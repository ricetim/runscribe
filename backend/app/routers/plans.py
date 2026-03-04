from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models import TrainingPlan, PlannedWorkout
from app.services.training_plans.daniels import generate_daniels_plan
from app.services.training_plans.pfitzinger import generate_pfitzinger_plan
from datetime import date

router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.get("")
def list_plans(session: Session = Depends(get_session)):
    return session.exec(select(TrainingPlan)).all()


@router.post("", status_code=201)
def create_plan(data: dict, session: Session = Depends(get_session)):
    source = data.get("source")
    goal_race_date = date.fromisoformat(data["goal_race_date"])

    if source == "daniels":
        workouts_data = generate_daniels_plan(
            goal_distance=data["goal_distance"],
            goal_race_date=goal_race_date,
            target_vdot=float(data["target_vdot"]),
        )
        start = workouts_data[0]["scheduled_date"]
    elif source == "pfitzinger":
        workouts_data = generate_pfitzinger_plan(
            goal_race_date=goal_race_date,
            peak_weekly_km=float(data.get("peak_weekly_km", 88)),
        )
        start = workouts_data[0]["scheduled_date"]
    else:
        raise HTTPException(status_code=422, detail="source must be 'daniels' or 'pfitzinger'")

    plan = TrainingPlan(
        name=data.get("name", f"{source.title()} {data.get('goal_distance', 'marathon')} plan"),
        source=source,
        goal_race_date=goal_race_date,
        goal_distance=data.get("goal_distance", "marathon"),
        start_date=start,
        target_vdot=data.get("target_vdot"),
        peak_weekly_km=data.get("peak_weekly_km"),
        notes=data.get("notes"),
    )
    session.add(plan)
    session.flush()

    for wd in workouts_data:
        session.add(PlannedWorkout(training_plan_id=plan.id, **wd))

    session.commit()
    session.refresh(plan)
    return plan


@router.get("/{plan_id}")
def get_plan(plan_id: int, session: Session = Depends(get_session)):
    plan = session.get(TrainingPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404)
    return plan


@router.get("/{plan_id}/workouts")
def get_workouts(plan_id: int, session: Session = Depends(get_session)):
    if not session.get(TrainingPlan, plan_id):
        raise HTTPException(status_code=404)
    workouts = session.exec(
        select(PlannedWorkout)
        .where(PlannedWorkout.training_plan_id == plan_id)
        .order_by(PlannedWorkout.scheduled_date)
    ).all()
    today = date.today()
    result = []
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
        result.append({**w.model_dump(), "status": status})
    return result


@router.patch("/{plan_id}/workouts/{workout_id}")
def update_workout(plan_id: int, workout_id: int, data: dict,
                   session: Session = Depends(get_session)):
    workout = session.get(PlannedWorkout, workout_id)
    if not workout or workout.training_plan_id != plan_id:
        raise HTTPException(status_code=404)
    if "completed_activity_id" in data:
        workout.completed_activity_id = data["completed_activity_id"]
    session.add(workout)
    session.commit()
    session.refresh(workout)
    return workout


@router.delete("/{plan_id}", status_code=204)
def delete_plan(plan_id: int, session: Session = Depends(get_session)):
    plan = session.get(TrainingPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404)
    for w in session.exec(select(PlannedWorkout).where(
        PlannedWorkout.training_plan_id == plan_id
    )).all():
        session.delete(w)
    session.delete(plan)
    session.commit()
