from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from . import models  # Register model metadata before creating tables.
from .database import Base, engine
from .routes_user import router as user_router
from .routes_wardrobe import UPLOAD_DIR, router as wardrobe_router
from .wardrobe import initialize_background_removal

app = FastAPI(title="AI Virtual Stylist API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wardrobe_router)
app.include_router(user_router)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.on_event("startup")
def create_database_tables() -> None:
    Base.metadata.create_all(bind=engine)
    # create_all does not add columns to existing tables; keep older local DBs usable.
    if "colour_detailed" not in {
        column["name"] for column in inspect(engine).get_columns("wardrobe_items")
    }:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE wardrobe_items ADD COLUMN colour_detailed VARCHAR")
            )
    user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
    with engine.begin() as connection:
        for column in ("height_cm", "bust_cm", "waist_cm", "hip_cm"):
            if column not in user_columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {column} FLOAT"))
    initialize_background_removal()


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
