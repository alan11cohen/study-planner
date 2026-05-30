from datetime import date, timedelta

from .core.database import SessionLocal
from .core.security import hash_password
from .models.study_plan import StudyPlan
from .models.study_task import StudyTask
from .models.user import User

_PLANS = [
    {
        "goal": "Pass AWS Solutions Architect Exam",
        "description": "Prepare for the SAA-C03 certification covering core cloud services and architecture patterns.",
        "hours_per_week": 8,
        "target_days": 60,
        "tasks": [
            ("Study EC2 fundamentals and instance types", 3, False),
            ("Study S3 and storage services", 2, False),
            ("Practice IAM policies and roles", 2, False),
            ("Complete practice exam 1", 4, True),
            ("Review VPC networking and subnets", 3, False),
        ],
    },
    {
        "goal": "Learn TypeScript Fundamentals",
        "description": "Build a solid foundation in TypeScript to use across React and Node.js projects.",
        "hours_per_week": 5,
        "target_days": None,
        "tasks": [
            ("Install TypeScript and set up the environment", 1, True),
            ("Read TypeScript handbook chapters 1-3", 2, True),
            ("Practice generics and utility types", 2, False),
            ("Build a small project with strict TypeScript", 4, False),
            ("Complete TypeScript course exercises", 3, False),
        ],
    },
    {
        "goal": "Read Clean Code by Robert C. Martin",
        "description": "Work through the book and apply its principles to real codebases.",
        "hours_per_week": 3,
        "target_days": None,
        "tasks": [
            ("Chapters 1-4: Meaningful names and functions", 2, True),
            ("Chapters 5-8: Formatting, objects, and error handling", 2, True),
            ("Chapters 9-11: Unit tests and classes", 2, True),
            ("Apply clean code principles to an existing project", 3, True),
        ],
    },
    {
        "goal": "Set Up CI/CD with GitHub Actions",
        "description": "Automate testing and deployment for a Python + React project using GitHub Actions.",
        "hours_per_week": 4,
        "target_days": None,
        "tasks": [
            ("Understand GitHub Actions concepts: workflows, jobs, steps", 1, True),
            ("Write a workflow to run backend tests on every push", 2, True),
            ("Write a workflow to run frontend type-check and build", 2, True),
            ("Add Docker build and push to GitHub Container Registry", 2, True),
            ("Configure environment secrets for deployment", 1, True),
        ],
    },
    {
        "goal": "Prepare for System Design Interviews",
        "description": "Study large-scale distributed systems to ace senior engineering interviews.",
        "hours_per_week": 6,
        "target_days": 45,
        "tasks": [
            ("Horizontal vs vertical scaling and load balancing", 2, True),
            ("Database sharding, replication, and indexing", 3, False),
            ("Design a URL shortener (Bitly-style)", 2, False),
            ("Design a Twitter-style news feed", 3, False),
            ("CAP theorem and consistency models", 2, False),
            ("Mock system design interview session", 1, False),
        ],
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter_by(name="admin").first():
            print("Seed data already present, skipping.")
            return

        user = User(name="admin", password_hash=hash_password("admin123"))
        db.add(user)
        db.flush()

        today = date.today()
        for plan_data in _PLANS:
            target = (
                today + timedelta(days=plan_data["target_days"])
                if plan_data["target_days"]
                else None
            )
            plan = StudyPlan(
                user_id=user.id,
                goal=plan_data["goal"],
                description=plan_data["description"],
                hours_per_week=plan_data["hours_per_week"],
                target_date=target,
            )
            db.add(plan)
            db.flush()

            for title, hours, completed in plan_data["tasks"]:
                db.add(
                    StudyTask(
                        plan_id=plan.id,
                        title=title,
                        estimated_hours=hours,
                        completed=completed,
                    )
                )

        db.commit()
        print("Seed complete: admin / admin123")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
