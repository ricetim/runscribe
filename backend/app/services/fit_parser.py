from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import fitparse


@dataclass
class FitParseResult:
    started_at: datetime
    distance_m: float
    duration_s: int
    elevation_gain_m: float
    avg_hr: Optional[int]
    sport_type: str
    datapoints: list[dict[str, Any]] = field(default_factory=list)


def parse_fit_file(path: Path) -> FitParseResult:
    if not path.exists():
        raise FileNotFoundError(f"FIT file not found: {path}")

    fitfile = fitparse.FitFile(str(path))
    records: list[dict] = []
    session_data: dict = {}
    sport_type = "run"

    for record in fitfile.get_messages("record"):
        row = {f.name: f.value for f in record if f.value is not None}
        if row:
            records.append(row)

    for msg in fitfile.get_messages("session"):
        session_data = {f.name: f.value for f in msg if f.value is not None}

    for msg in fitfile.get_messages("sport"):
        sport_val = {f.name: f.value for f in msg}.get("sport", "running")
        sport_type = str(sport_val).lower().replace(" ", "_")

    # Determine start time — prefer session header, fall back to first record
    started_at = session_data.get("start_time")
    if started_at is None and records:
        started_at = records[0].get("timestamp")
    if started_at is None:
        started_at = datetime.now(timezone.utc)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    distance_m = float(session_data.get("total_distance") or 0)
    duration_s = int(session_data.get("total_elapsed_time") or 0)
    elevation_gain_m = float(session_data.get("total_ascent") or 0)
    avg_hr = session_data.get("avg_heart_rate")

    # Semicircle → decimal degrees conversion factor (2^31 / 180)
    SEMICIRCLE = 11930465

    datapoints = []
    for r in records:
        ts = r.get("timestamp")
        if ts is None:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        pos_lat = r.get("position_lat")
        pos_lon = r.get("position_long")

        # Cadence in FIT is stored as revolutions/min for one foot;
        # multiply by 2 for total steps/min (running cadence convention)
        raw_cadence = r.get("cadence")
        cadence = raw_cadence * 2 if raw_cadence is not None else None

        datapoints.append({
            "timestamp": ts,
            "lat": pos_lat / SEMICIRCLE if pos_lat is not None else None,
            "lon": pos_lon / SEMICIRCLE if pos_lon is not None else None,
            "distance_m": r.get("distance"),
            "speed_m_s": r.get("speed"),
            "heart_rate": r.get("heart_rate"),
            "cadence": cadence,
            "altitude_m": r.get("altitude"),
            "power_w": r.get("power"),
        })

    return FitParseResult(
        started_at=started_at,
        distance_m=distance_m,
        duration_s=duration_s,
        elevation_gain_m=elevation_gain_m,
        avg_hr=int(avg_hr) if avg_hr is not None else None,
        sport_type=sport_type,
        datapoints=datapoints,
    )
