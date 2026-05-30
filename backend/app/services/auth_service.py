from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..core.security import create_token, hash_password, verify_password
from ..models.user import User
from ..schemas.auth import LoginInput, RegisterInput, TokenResponse
from ..schemas.user import UserRead


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, data: RegisterInput) -> TokenResponse:
        if self.db.query(User).filter(User.name == data.name).first():
            raise HTTPException(status_code=409, detail="Username already taken")
        user = User(name=data.name, password_hash=hash_password(data.password))
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return TokenResponse(
            access_token=create_token(user.id, user.name),
            user=UserRead.model_validate(user),
        )

    def login(self, data: LoginInput) -> TokenResponse:
        user = self.db.query(User).filter(User.name == data.name).first()
        if (
            not user
            or not user.password_hash
            or not verify_password(data.password, user.password_hash)
        ):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        return TokenResponse(
            access_token=create_token(user.id, user.name),
            user=UserRead.model_validate(user),
        )
