import pytest
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "sample.fit"


def test_list_activities_empty(client):
    r = client.get("/api/activities")
    assert r.status_code == 200
    assert r.json() == []


def test_get_nonexistent_activity(client):
    r = client.get("/api/activities/999")
    assert r.status_code == 404


def test_get_activity_datapoints_nonexistent(client):
    r = client.get("/api/activities/999/datapoints")
    assert r.status_code == 404


def test_get_activity_photos_nonexistent(client):
    r = client.get("/api/activities/999/photos")
    assert r.status_code == 404


def test_upload_invalid_file(client, tmp_path, monkeypatch):
    import app.config as cfg
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    r = client.post(
        "/api/activities/upload",
        files={"file": ("bad.fit", b"not a fit file", "application/octet-stream")},
    )
    assert r.status_code == 422


@pytest.mark.skipif(not FIXTURE.exists(), reason="no sample.fit fixture")
def test_upload_fit_file(client, tmp_path, monkeypatch):
    import app.config as cfg
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    with open(FIXTURE, "rb") as f:
        r = client.post(
            "/api/activities/upload",
            files={"file": ("run.fit", f, "application/octet-stream")},
        )
    assert r.status_code == 201
    body = r.json()
    assert body["id"] is not None
    assert body["distance_m"] > 0
    assert body["source"] == "manual_upload"


@pytest.mark.skipif(not FIXTURE.exists(), reason="no sample.fit fixture")
def test_list_activities_after_upload(client, tmp_path, monkeypatch):
    import app.config as cfg
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    with open(FIXTURE, "rb") as f:
        client.post("/api/activities/upload",
                    files={"file": ("run.fit", f, "application/octet-stream")})
    r = client.get("/api/activities")
    assert r.status_code == 200
    assert len(r.json()) == 1
