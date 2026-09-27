from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="Guest", nullable=False)
    body_type = Column(String, nullable=True)
    skin_tone = Column(String, nullable=True)
    preferred_colours = Column(String, nullable=True)
    style_preference = Column(String, nullable=True)

    wardrobe_items = relationship(
        "WardrobeItem", back_populates="user", cascade="all, delete-orphan"
    )
    feedback = relationship(
        "Feedback", back_populates="user", cascade="all, delete-orphan"
    )


class WardrobeItem(Base):
    __tablename__ = "wardrobe_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_path = Column(String, nullable=False)
    category = Column(String, nullable=False)
    subcategory = Column(String, nullable=True)
    colour = Column(String, nullable=True)
    colour_detailed = Column(String, nullable=True)
    pattern = Column(String, nullable=True)
    style = Column(String, nullable=True)
    fit = Column(String, nullable=True)
    season = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="wardrobe_items")


class Outfit(Base):
    __tablename__ = "outfits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    occasion = Column(String, nullable=True)
    date = Column(DateTime, nullable=True)
    item_ids = Column(String, nullable=False)
    score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tag = Column(String, nullable=False)
    liked = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="feedback")
