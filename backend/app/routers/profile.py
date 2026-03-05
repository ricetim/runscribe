from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.models import UserProfile

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("")
def get_profile(session: Session = Depends(get_session)):
    profile = session.get(UserProfile, 1)
    return profile or UserProfile(id=1)


@router.patch("")
def update_profile(data: dict, session: Session = Depends(get_session)):
    profile = session.get(UserProfile, 1)
    if not profile:
        profile = UserProfile(id=1)
        session.add(profile)
    for key in {"hr_max", "hr_rest", "weight_kg"}:
        if key in data:
            setattr(profile, key, data[key])
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile
