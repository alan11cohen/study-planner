from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..repositories.user_repository import UserRepository
from ..schemas.user import UserCreate, UserRead


class UserService:
    def __init__(self, db: Session) -> None:
        self.repo = UserRepository(db)

    def create_user(self, data: UserCreate) -> UserRead:
        user = self.repo.create(data)
        return UserRead.model_validate(user)

    def get_user(self, user_id: int) -> UserRead:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserRead.model_validate(user)

    def get_all_users(self) -> list[UserRead]:
        return [UserRead.model_validate(u) for u in self.repo.get_all()]
