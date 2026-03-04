from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from app.database import get_session
from app.models import Shoe, ActivityShoe, Activity

router = APIRouter(prefix="/api/shoes", tags=["shoes"])


@router.get("")
def list_shoes(session: Session = Depends(get_session)):
    shoes = session.exec(select(Shoe)).all()
    result = []
    for shoe in shoes:
        dist = session.exec(
            select(func.sum(Activity.distance_m))
            .join(ActivityShoe, ActivityShoe.activity_id == Activity.id)
            .where(ActivityShoe.shoe_id == shoe.id)
        ).first() or 0.0
        result.append({**shoe.model_dump(), "total_distance_km": round(dist / 1000, 1)})
    return result


@router.post("", status_code=201)
def create_shoe(shoe: Shoe, session: Session = Depends(get_session)):
    session.add(shoe)
    session.commit()
    session.refresh(shoe)
    return shoe


@router.patch("/{shoe_id}")
def update_shoe(shoe_id: int, data: dict, session: Session = Depends(get_session)):
    shoe = session.get(Shoe, shoe_id)
    if not shoe:
        raise HTTPException(status_code=404)
    for k in {"name", "brand", "retired", "notes", "retirement_threshold_km"}:
        if k in data:
            setattr(shoe, k, data[k])
    session.add(shoe)
    session.commit()
    session.refresh(shoe)
    return shoe
