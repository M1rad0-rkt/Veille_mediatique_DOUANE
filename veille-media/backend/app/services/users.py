from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Role, User
from app.schemas.user import UserCreate


def create_user(db: Session, data: UserCreate) -> User:
    email = data.email.lower()
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(409, "Un compte existe déjà avec cet e-mail")
    role = db.scalar(select(Role).where(Role.name == data.role))
    user = User(email=email, full_name=data.full_name.strip(),
                password_hash=hash_password(data.password), role_id=role.id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
