from pathlib import Path
from typing import Generator

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Keep the database beside this app's parent directory: backend/stylist.db.
DATABASE_URL = URL.create(
    "sqlite", database=str(Path(__file__).resolve().parent.parent / "stylist.db")
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
