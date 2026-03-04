"""
Coros sync via unofficial Training Hub API.
Switch to the official partner API once access is granted.
"""
import httpx
from app.config import COROS_EMAIL, COROS_PASSWORD

BASE = "https://trainingapi.coros.com"


def login(email: str, password: str) -> str:
    r = httpx.post(f"{BASE}/account/login",
                   json={"account": email, "pwd": password}, timeout=15)
    r.raise_for_status()
    return r.json()["data"]["accessToken"]


def list_activities(token: str, page: int = 1, size: int = 20) -> list[dict]:
    r = httpx.get(f"{BASE}/activity/query",
                  params={"pageNumber": page, "pageSize": size},
                  headers={"accesstoken": token}, timeout=15)
    r.raise_for_status()
    return r.json().get("data", {}).get("dataList", [])


def download_fit(token: str, sport_type: str, label_id: str) -> bytes:
    r = httpx.get(f"{BASE}/activity/fit/url",
                  params={"sportType": sport_type, "labelId": label_id},
                  headers={"accesstoken": token}, timeout=15)
    r.raise_for_status()
    url = r.json()["data"]["fileUrl"]
    return httpx.get(url, timeout=30).content


def get_training_notes(token: str, label_id: str) -> str | None:
    """Fetch post-workout notes for an activity."""
    try:
        r = httpx.get(f"{BASE}/activity/detail",
                      params={"labelId": label_id},
                      headers={"accesstoken": token}, timeout=15)
        return r.json().get("data", {}).get("remark")
    except Exception:
        return None
