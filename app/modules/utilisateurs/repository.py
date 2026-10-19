
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


def get_users_by_role(db: Session, role: str) -> list[User]:
    statement = (
        select(User)
        .where(User.role == role)
        .order_by(User.created_at.desc())
    )
    return list(db.scalars(statement).all())


def create_user(
    db: Session,
    full_name: str,
    phone: str,
    email: str,
    password_hash: str,
    role: str = "user",
) -> User:
    user = User(
        full_name=full_name,
        phone=phone,
        email=email,
        password_hash=password_hash,
        role=role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user



def get_all_users(db: Session) -> list[User]:
    statement = select(User).order_by(User.created_at.desc())
    return list(db.scalars(statement).all())
