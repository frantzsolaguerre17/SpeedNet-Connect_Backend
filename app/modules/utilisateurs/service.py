
from sqlalchemy.orm import Session

from app.core.security import hacher_mot_de_passe, verifier_mot_de_passe
from app.modules.utilisateurs import repository
from app.modules.utilisateurs.model import User
from app.modules.utilisateurs.schema import UtilisateurCreate


def register_user(
    db: Session,
    user_data: UtilisateurCreate,
) -> User:
    return create_user_account(
        db=db,
        user_data=user_data,
        role="user",
    )


def create_user_account(
    db: Session,
    user_data: UtilisateurCreate,
    role: str,
) -> User:
    if role not in ("user", "admin"):
        raise ValueError("Rôle invalide")

    existing_email = repository.get_user_by_email(
        db,
        str(user_data.email),
    )
    if existing_email:
        raise ValueError("Email already registered")

    existing_phone = repository.get_user_by_phone(
        db,
        user_data.phone,
    )
    if existing_phone:
        raise ValueError("Phone number already registered")

    hashed_password = hacher_mot_de_passe(user_data.password)

    return repository.create_user(
        db=db,
        full_name=user_data.full_name,
        phone=user_data.phone,
        email=str(user_data.email),
        password_hash=hashed_password,
        role=role,
    )


def list_clients(db: Session) -> list[User]:
    return repository.get_users_by_role(db, "user")


def login_user(
    db: Session,
    phone: str,
    password: str,
) -> User:
    user = repository.get_user_by_phone(db, phone)

    if user is None:
        raise ValueError("Invalid phone number or password")

    if not verifier_mot_de_passe(password, user.password_hash):
        raise ValueError("Invalid phone number or password")

    if user.status != "active":
        raise ValueError("User account is inactive")

    return user


def list_all_users(db: Session) -> list[User]:
    return repository.get_all_users(db)
