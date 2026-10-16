
from sqlalchemy.orm import Session

from app.core.security import hacher_mot_de_passe, verifier_mot_de_passe
from app.modules.utilisateurs import repository
from app.modules.utilisateurs.model import User
from app.modules.utilisateurs.schema import UtilisateurCreate


def register_user(
    db: Session,
    user_data: UtilisateurCreate,
) -> User:
    # Check whether the email already exists
    existing_email = repository.get_user_by_email(
        db,
        str(user_data.email),
    )
    if existing_email:
        raise ValueError("Email already registered")

    # Check whether the phone number already exists
    existing_phone = repository.get_user_by_phone(
        db,
        user_data.phone,
    )
    if existing_phone:
        raise ValueError("Phone number already registered")

    # Hash the password before saving it
    hashed_password = hacher_mot_de_passe(user_data.password)

    # Create the user in the database
    return repository.create_user(
        db=db,
        full_name=user_data.full_name,
        phone=user_data.phone,
        email=str(user_data.email),
        password_hash=hashed_password,
    )




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
