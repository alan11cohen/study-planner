from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=True)

    plans = relationship(
        "StudyPlan", back_populates="user", cascade="all, delete-orphan"
    )
