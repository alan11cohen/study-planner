from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    goal = Column(String, nullable=False)
    hours_per_week = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    target_date = Column(Date, nullable=True)

    user = relationship("User", back_populates="plans")
    tasks = relationship(
        "StudyTask", back_populates="plan", cascade="all, delete-orphan"
    )
