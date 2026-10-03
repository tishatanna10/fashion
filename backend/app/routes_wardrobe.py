from pathlib import Path
from logging import getLogger
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .database import get_db
from .models import User, WardrobeItem
from .wardrobe import analyze_clothing_image


router = APIRouter(prefix="/api/wardrobe", tags=["wardrobe"])
logger = getLogger(__name__)
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}


class WardrobeItemUpdate(BaseModel):
    category: str | None = None
    subcategory: str | None = None
    colour: str | None = None
    colour_detailed: str | None = None
    pattern: str | None = None
    style: str | None = None
    fit: str | None = None
    season: str | None = None


def _item_response(item: WardrobeItem, confidence: dict | None = None) -> dict:
    result = {
        "id": item.id,
        "user_id": item.user_id,
        "image_path": item.image_path,
        "category": item.category,
        "subcategory": item.subcategory,
        "colour": item.colour,
        "colour_detailed": item.colour_detailed,
        "pattern": item.pattern,
        "style": item.style,
        "fit": item.fit,
        "season": item.season,
        "created_at": item.created_at,
    }
    if confidence is not None:
        result["confidence"] = confidence
    return result


@router.post("/upload")
async def upload_wardrobe_item(
    file: UploadFile = File(...),
    user_id: int = Form(1),
    db: Session = Depends(get_db),
) -> dict:
    request_started_at = perf_counter()
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Upload a supported image file")

    user = db.get(User, user_id)
    if user is None and user_id == 1:
        user = User(id=1, name="Guest")
        db.add(user)
        db.commit()
    elif user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} was not found")

    suffix = Path(file.filename or "upload.jpg").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        suffix = ".jpg" if file.content_type == "image/jpeg" else ".png"
    filename = f"{uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / filename
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")
    destination.write_bytes(content)

    try:
        # Background removal and CLIP inference are synchronous and CPU/GPU
        # bound. Keep them off the asyncio event loop used by FastAPI.
        analysis = await run_in_threadpool(analyze_clothing_image, str(destination))
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Could not analyze image: {exc}") from exc
    finally:
        await file.close()

    item = WardrobeItem(
        user_id=user_id,
        image_path=f"uploads/{filename}",
        category=analysis["category"],
        style=analysis["style"],
        pattern=analysis["pattern"],
        colour=analysis["colour"],
        colour_detailed=analysis["colour_detailed"],
        subcategory=analysis["subcategory"],
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    logger.info(
        "wardrobe upload complete user_id=%s item_id=%s elapsed_s=%.2f",
        user_id,
        item.id,
        perf_counter() - request_started_at,
    )
    response = _item_response(item, analysis["confidence"])
    response["category_candidates"] = analysis["category_candidates"]
    response["style_candidates"] = analysis["style_candidates"]
    return response


@router.get("/{user_id}")
def get_wardrobe(user_id: int, db: Session = Depends(get_db)) -> list[dict]:
    items = (
        db.query(WardrobeItem)
        .filter(WardrobeItem.user_id == user_id)
        .order_by(WardrobeItem.created_at.desc())
        .all()
    )
    return [_item_response(item) for item in items]


@router.patch("/{item_id}")
def update_wardrobe_item(
    item_id: int,
    updates: WardrobeItemUpdate,
    db: Session = Depends(get_db),
) -> dict:
    item = db.get(WardrobeItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")
    changes = updates.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="Provide at least one field to update")
    for field, value in changes.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return _item_response(item)


@router.delete("/{item_id}")
def delete_wardrobe_item(item_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    item = db.get(WardrobeItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")

    original_path = UPLOAD_DIR / Path(item.image_path).name
    cleaned_path = original_path.with_name(f"{original_path.stem}_nobg.png")
    db.delete(item)
    db.commit()

    for image_path in (original_path, cleaned_path):
        try:
            image_path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove wardrobe image file %s", image_path)

    return {"message": "Wardrobe item deleted successfully"}
