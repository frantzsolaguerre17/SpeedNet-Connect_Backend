
from getpass import getpass

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.modules.utilisateurs import repository
from app.modules.utilisateurs.model import User
from app.core.security import hacher_mot_de_passe


def main():
    full_name = input("Nom complet de l'administrateur : ").strip()
    phone = input("Téléphone : ").strip()
    email = input("Adresse e-mail : ").strip().lower()
    password = getpass("Mot de passe administrateur : ")
    confirm_password = getpass("Confirme le mot de passe : ")

    if not full_name or not phone or not email:
        print("Erreur : tous les champs sont obligatoires.")
        return

    if len(password) < 8 or len(password) > 128:
        print("Erreur : le mot de passe doit contenir entre 8 et 128 caractères.")
        return

    if password != confirm_password:
        print("Erreur : les mots de passe ne correspondent pas.")
        return

    db: Session = SessionLocal()

    try:
        if repository.get_user_by_email(db, email):
            print("Erreur : cette adresse e-mail est déjà utilisée.")
            return

        if repository.get_user_by_phone(db, phone):
            print("Erreur : ce numéro de téléphone est déjà utilisé.")
            return

        admin = User(
            full_name=full_name,
            phone=phone,
            email=email,
            password_hash=hacher_mot_de_passe(password),
            role="admin",
            status="active",
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("\nAdministrateur créé avec succès !")
        print(f"ID : {admin.id}")
        print(f"Nom : {admin.full_name}")
        print(f"E-mail : {admin.email}")
        print(f"Rôle : {admin.role}")

    except Exception:
        db.rollback()
        print(
            "Erreur lors de la création. "
            "Vérifie la connexion à la base de données."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
