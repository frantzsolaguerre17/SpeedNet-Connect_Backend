
from sqlalchemy.orm import Session

from app.core.security import hacher_mot_de_passe, verifier_mot_de_passe
from app.modules.utilisateurs import repository
from app.modules.utilisateurs.model import User
from app.modules.utilisateurs.schema import UtilisateurCreate
from app.modules.wallets.model import Wallet


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

    existing_phone = repository.get_user_by_phone(
        db,
        user_data.phone,
    )
    if existing_phone:
        raise ValueError("Ce numéro de téléphone est déjà enregistré.")

    hashed_password = hacher_mot_de_passe(user_data.password)

    try:
        user = repository.create_user(
            db=db,
            full_name=user_data.full_name,
            phone=user_data.phone,
            password_hash=hashed_password,
            role=role,
        )

        wallet = Wallet(
            user_id=user.id,
            balance=0,
            currency="HTG",
        )
        db.add(wallet)
        db.commit()
        db.refresh(user)

        return user

    except Exception:
        db.rollback()
        raise



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
