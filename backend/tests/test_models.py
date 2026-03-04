from datetime import datetime, timezone, date
from app.models import Activity, DataPoint, Shoe, ActivityShoe, Goal, Photo
from app.models import TrainingPlan, PlannedWorkout


def test_create_activity(session):
    act = Activity(
        source="manual_upload",
        started_at=datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc),
        distance_m=10000.0,
        duration_s=3600,
        sport_type="run",
    )
    session.add(act)
    session.commit()
    session.refresh(act)
    assert act.id is not None
    assert act.distance_m == 10000.0


def test_photo_has_gps_fields(session):
    act = Activity(source="manual_upload", started_at=datetime.now(timezone.utc),
                   distance_m=5000, duration_s=1800, sport_type="run")
    session.add(act)
    session.commit()
    photo = Photo(activity_id=act.id, url="https://example.com/photo.jpg",
                  lat=37.7749, lon=-122.4194)
    session.add(photo)
    session.commit()
    session.refresh(photo)
    assert photo.lat == 37.7749
    assert photo.lon == -122.4194


def test_create_training_plan(session):
    plan = TrainingPlan(
        name="Daniels 5K Plan",
        source="daniels",
        goal_race_date=date(2026, 6, 1),
        goal_distance="5k",
        start_date=date(2026, 3, 1),
        target_vdot=50.0,
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)
    assert plan.id is not None


def test_planned_workout_links_activity(session):
    act = Activity(source="manual_upload", started_at=datetime.now(timezone.utc),
                   distance_m=10000, duration_s=3600, sport_type="run")
    plan = TrainingPlan(name="Test", source="daniels",
                        goal_race_date=date(2026, 6, 1),
                        goal_distance="marathon", start_date=date(2026, 3, 1))
    session.add(act)
    session.add(plan)
    session.commit()
    workout = PlannedWorkout(
        training_plan_id=plan.id,
        scheduled_date=date(2026, 3, 5),
        week_number=1,
        workout_type="easy",
        description="8 km easy",
        target_distance_m=8000,
        completed_activity_id=act.id,
    )
    session.add(workout)
    session.commit()
    session.refresh(workout)
    assert workout.completed_activity_id == act.id
