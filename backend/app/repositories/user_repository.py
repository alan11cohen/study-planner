from sqlalchemy.orm import Session

from ..models.user import User
from ..schemas.user import UserCreate


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: UserCreate) -> User:
        user = User(**data.model_dump())
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_all(self) -> list[User]:
        return self.db.query(User).order_by(User.id).all()
