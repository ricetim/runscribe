from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import fitdecode


@dataclass
class FitParseResult:
    started_at: datetime
    distance_m: float
    duration_s: int
    elevation_gain_m: float
    avg_hr: Optional[int]
    sport_type: str
    datapoints: list[dict[str, Any]] = field(default_factory=list)


def _get(frame, name):
    """Safely get a field value from a fitdecode data message."""
    if frame.has_field(name):
        return frame.get_value(name)
    return None


def _tz(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def parse_fit_file(path: Path) -> FitParseResult:
    if not path.exists():
        raise FileNotFoundError(f"FIT file not found: {path}")

    records: list[dict] = []
    session_data: dict = {}
    sport_type = "run"

    with fitdecode.FitReader(str(path), error_handling=fitdecode.ErrorHandling.IGNORE) as fit:
        for frame in fit:
            if not isinstance(frame, fitdecode.FitDataMessage):
                continue

            if frame.name == "record":
                row = {}
                for field_def in frame.fields:
                    if field_def.value is not None:
                        row[field_def.name] = field_def.value
                if row:
                    records.append(row)

            elif frame.name == "session":
                for field_def in frame.fields:
                    if field_def.value is not None:
                        session_data[field_def.name] = field_def.value

            elif frame.name == "sport":
                sport_val = _get(frame, "sport")
                if sport_val is not None:
                    sport_type = str(sport_val).lower().replace(" ", "_")

    # Determine start time
    started_at = _tz(session_data.get("start_time"))
    if started_at is None and records:
        started_at = _tz(records[0].get("timestamp"))
    if started_at is None:
        started_at = datetime.now(timezone.utc)

    distance_m = float(session_data.get("total_distance") or 0)
    duration_s = int(session_data.get("total_elapsed_time") or 0)
    elevation_gain_m = float(session_data.get("total_ascent") or 0)
    avg_hr = session_data.get("avg_heart_rate")

    # Semicircle → decimal degrees conversion factor (2^31 / 180)
    SEMICIRCLE = 11930465

    datapoints = []
    for r in records:
        ts = _tz(r.get("timestamp"))
        if ts is None:
            continue

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
            # Running dynamics
            "vertical_oscillation_mm": r.get("vertical_oscillation"),
            "stride_length_m": r.get("stride_length"),
            "vertical_ratio": r.get("vertical_ratio"),
            "stance_time_ms": r.get("stance_time"),
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
