"""User profile endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from .body_type import calculate_body_type
from .database import get_db
from .models import User


router = APIRouter(prefix="/api/users", tags=["users"])


class UserCreate(BaseModel):
    name: str = "Guest"
    skin_tone: str | None = None
    preferred_colours: list[str] | None = None
    style_preference: str | None = None
    height_cm: float | None = Field(default=None, gt=0)
    bust_cm: float | None = Field(default=None, gt=0)
    waist_cm: float | None = Field(default=None, gt=0)
    hip_cm: float | None = Field(default=None, gt=0)


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "Guest"
    skin_tone: str | None = None
    preferred_colours: list[str] | None = None
    style_preference: str | None = None
    height_cm: float | None = Field(default=None, gt=0)
    bust_cm: float | None = Field(default=None, gt=0)
    waist_cm: float | None = Field(default=None, gt=0)
    hip_cm: float | None = Field(default=None, gt=0)


def _user_response(user: User) -> dict:
    colours = user.preferred_colours
    return {
        "id": user.id,
        "name": user.name,
        "body_type": user.body_type,
        "skin_tone": user.skin_tone,
        "preferred_colours": (
            [colour.strip() for colour in colours.split(",") if colour.strip()]
            if colours
            else []
        ),
        "style_preference": user.style_preference,
        "height_cm": user.height_cm,
        "bust_cm": user.bust_cm,
        "waist_cm": user.waist_cm,
        "hip_cm": user.hip_cm,
    }


@router.post("")
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> dict:
    data = payload.model_dump()
    preferred_colours = data.pop("preferred_colours")
    data["preferred_colours"] = (
        ",".join(colour.strip() for colour in preferred_colours if colour.strip())
        if preferred_colours
        else None
    )
    data["body_type"] = calculate_body_type(
        data["bust_cm"], data["waist_cm"], data["hip_cm"]
    )
    user = User(**data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_response(user)


@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_response(user)


@router.patch("/{user_id}")
def update_user(
    user_id: int, payload: UserUpdate, db: Session = Depends(get_db)
) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    changes = payload.model_dump(exclude_unset=True)
    if "preferred_colours" in changes:
        colours = changes["preferred_colours"]
        changes["preferred_colours"] = (
            ",".join(colour.strip() for colour in colours if colour.strip())
            if colours
            else None
        )
    measurements = {"bust_cm", "waist_cm", "hip_cm"}
    for field, value in changes.items():
        setattr(user, field, value)
    if measurements.intersection(changes):
        user.body_type = calculate_body_type(user.bust_cm, user.waist_cm, user.hip_cm)

    db.commit()
    db.refresh(user)
    return _user_response(user)
