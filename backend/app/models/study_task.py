from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class StudyTask(Base):
    __tablename__ = "study_tasks"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("study_plans.id"), nullable=False)
    title = Column(String, nullable=False)
    estimated_hours = Column(Float, nullable=False)
    completed = Column(Boolean, nullable=False, default=False)

    plan = relationship("StudyPlan", back_populates="tasks")
