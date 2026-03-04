import io
import httpx
import exifread
from typing import Optional


def _dms_to_decimal(dms, ref: str) -> float:
    """Convert degrees/minutes/seconds + ref to decimal degrees."""
    d = float(dms[0].num) / float(dms[0].den)
    m = float(dms[1].num) / float(dms[1].den)
    s = float(dms[2].num) / float(dms[2].den)
    result = d + m / 60 + s / 3600
    if ref in ("S", "W"):
        result = -result
    return round(result, 7)


def extract_gps_from_url(url: str) -> tuple[Optional[float], Optional[float]]:
    """Download image and extract EXIF GPS. Returns (lat, lon) or (None, None)."""
    try:
        r = httpx.get(url, timeout=10)
        tags = exifread.process_file(io.BytesIO(r.content), details=False)
        lat_tag = tags.get("GPS GPSLatitude")
        lat_ref = tags.get("GPS GPSLatitudeRef")
        lon_tag = tags.get("GPS GPSLongitude")
        lon_ref = tags.get("GPS GPSLongitudeRef")
        if not (lat_tag and lon_tag):
            return None, None
        lat = _dms_to_decimal(lat_tag.values, str(lat_ref))
        lon = _dms_to_decimal(lon_tag.values, str(lon_ref))
        return lat, lon
    except Exception:
        return None, None
