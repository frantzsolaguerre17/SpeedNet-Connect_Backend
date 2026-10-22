

from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_admin
from app.core.security import creer_access_token
from app.db.dependencies import get_db
from app.modules.wallets.model import Wallet
from app.modules.utilisateurs import service
from app.modules.utilisateurs.model import User
from app.modules.utilisateurs.schema import (
    LoginResponse,
    UserLogin,
    UtilisateurCreate,
    UtilisateurResponse,
)

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.wallets.model import Wallet

router = APIRouter(prefix="/users", tags=["Users"])


class AdminCreateUser(UtilisateurCreate):
    role: Literal["user", "admin"] = "user"


class AdminMessage(BaseModel):
    message: str

class RechargeRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class RechargeResponse(BaseModel):
    message: str
    user_id: int
    balance: Decimal
    currency: str


class MonPortefeuilleResponse(BaseModel):
    balance: Decimal
    currency: str


@router.post(
    "/register",
    response_model=UtilisateurResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: UtilisateurCreate,
    db: Session = Depends(get_db),
):
    try:
        return service.register_user(db, user_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
):
    try:
        user = service.login_user(
            db=db,
            phone=credentials.phone,
            password=credentials.password,
        )

        token = creer_access_token(
            user_id=user.id,
            role=user.role,
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.post(
    "/admin/users",
    response_model=UtilisateurResponse,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_user(
    user_data: AdminCreateUser,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        return service.create_user_account(
            db=db,
            user_data=user_data,
            role=user_data.role,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/admin/clients",
    response_model=list[UtilisateurResponse],
)
def admin_list_clients(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return service.list_clients(db)


@router.get("/admin-test")
def admin_test(
    admin: Annotated[User, Depends(require_admin)],
):
    return {
        "message": "Accès administrateur autorisé",
        "role": admin.role,
    }


@router.get("/admin/users", response_model=list[UtilisateurResponse])
def admin_list_users(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return service.list_all_users(db)


@router.post(
    "/admin/users/{user_id}/recharge",
    response_model=RechargeResponse,
)
def admin_recharge_wallet(
    user_id: int,
    data: RechargeRequest,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    wallet = db.scalar(
        select(Wallet)
        .where(Wallet.user_id == user_id)
        .with_for_update()
    )

    if wallet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portefeuille introuvable pour cet utilisateur",
        )

    try:
        wallet.balance = wallet.balance + data.amount
        db.commit()
        db.refresh(wallet)

        return {
            "message": "Recharge effectuée avec succès",
            "user_id": user_id,
            "balance": wallet.balance,
            "currency": wallet.currency,
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la recharge",
        )


@router.get("/me/wallet", response_model=MonPortefeuilleResponse)
def obtenir_mon_portefeuille(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    wallet = db.scalar(
        select(Wallet).where(Wallet.user_id == current_user.id)
    )

    if wallet is None:
        return {
            "balance": Decimal("0.00"),
            "currency": "HTG",
        }

    return {
        "balance": wallet.balance,
        "currency": wallet.currency,
    }