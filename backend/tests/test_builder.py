import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlmodel import Session

from app.models import Activity, DataPoint, Goal, Shoe, TrainingPlan
from app.services.builder import rebuild_activity, rebuild_globals, rebuild_all, _tile_xy


@pytest.fixture
def act(session):
    a = Activity(
        source="manual_upload",
        started_at=datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc),
        distance_m=10000.0,
        duration_s=3600,
        elevation_gain_m=100.0,
        sport_type="run",
    )
    session.add(a)
    session.flush()
    session.add(DataPoint(
        activity_id=a.id,
        timestamp=datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc),
        lat=37.7749, lon=-122.4194, distance_m=0.0, speed_m_s=2.8,
    ))
    session.add(DataPoint(
        activity_id=a.id,
        timestamp=datetime(2026, 1, 1, 8, 30, tzinfo=timezone.utc),
        lat=37.7800, lon=-122.4100, distance_m=5000.0, speed_m_s=2.8,
    ))
    session.commit()
    session.refresh(a)
    return a


def test_tile_xy_known_value():
    # San Francisco at zoom 13: tile (1310, 3166)
    x, y = _tile_xy(37.7749, -122.4194, 13)
    assert x == 1310
    assert y == 3166


def test_rebuild_activity_writes_files(session, act, tmp_path):
    rebuild_activity(act.id, session, static_dir=tmp_path)

    activity_file = tmp_path / f"activity-{act.id}.json"
    datapoints_file = tmp_path / f"datapoints-{act.id}.json"

    assert activity_file.exists()
    assert datapoints_file.exists()

    data = json.loads(activity_file.read_text())
    assert data["activity"]["id"] == act.id
    assert data["activity"]["distance_m"] == 10000.0
    assert isinstance(data["laps"], list)
    assert len(data["track"]) == 2  # 2 GPS points
    assert data["track"][0] == [37.7749, -122.4194, 2.8]

    dps = json.loads(datapoints_file.read_text())
    assert len(dps) == 2
    assert dps[0]["activity_id"] == act.id


def test_rebuild_activity_missing_activity_is_noop(session, tmp_path):
    rebuild_activity(999, session, static_dir=tmp_path)
    assert not (tmp_path / "activity-999.json").exists()


def test_rebuild_globals_writes_all_files(session, act, tmp_path):
    rebuild_globals(session, static_dir=tmp_path)

    for filename in ["activities.json", "dashboard.json", "goals.json", "shoes.json", "plans.json"]:
        assert (tmp_path / filename).exists(), f"{filename} not found"

    acts = json.loads((tmp_path / "activities.json").read_text())
    assert len(acts) == 1
    assert acts[0]["id"] == act.id
    assert "track" in acts[0]

    dash = json.loads((tmp_path / "dashboard.json").read_text())
    assert "summary" in dash
    assert "week" in dash["summary"]
    assert "training_load" in dash
    assert "vdot" in dash
    assert "personal_bests" in dash


def test_rebuild_globals_empty_db(session, tmp_path):
    rebuild_globals(session, static_dir=tmp_path)
    acts = json.loads((tmp_path / "activities.json").read_text())
    assert acts == []


def test_rebuild_all(session, act, tmp_path):
    rebuild_all(session, static_dir=tmp_path, tile_dir=tmp_path / "tiles")

    assert (tmp_path / "activities.json").exists()
    assert (tmp_path / f"activity-{act.id}.json").exists()
    assert (tmp_path / f"datapoints-{act.id}.json").exists()
    assert (tmp_path / "dashboard.json").exists()
