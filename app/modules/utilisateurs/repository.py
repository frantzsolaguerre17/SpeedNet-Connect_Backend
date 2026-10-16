
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.utilisateurs.model import User


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return db.scalar(statement)


def get_user_by_phone(db: Session, phone: str) -> User | None:
    statement = select(User).where(User.phone == phone)
    return db.scalar(statement)


def create_user(
    db: Session,
    full_name: str,
    phone: str,
    email: str,
    password_hash: str,
) -> User:
    user = User(
        full_name=full_name,
        phone=phone,
        email=email,
        password_hash=password_hash,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user
