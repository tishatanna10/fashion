from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # Register model metadata before creating tables.
from .database import Base, engine

app = FastAPI(title="AI Virtual Stylist API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_database_tables() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
