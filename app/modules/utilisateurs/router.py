

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
from app.modules.wallets.transaction_model import WalletTransaction
from app.modules.wallets.transaction_model import WalletTransaction
from app.modules.plans_wifi.order_model import Order
from app.modules.plans_wifi.model import Plan
import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.modules.plans_wifi.model import Plan, WifiCode


logger = logging.getLogger(__name__)

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



@router.get("/admin/stats")
def admin_stats(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    # 1. Nombre total de comptes clients (sans les administrateurs)
    clients_inscrits = db.scalar(
        select(func.count(User.id)).where(
            func.lower(User.role) == "user"
        )
    ) or 0

    # 2. Total des ventes confirmées aujourd'hui, en HTG
    maintenant = datetime.now().astimezone()
    debut_jour = maintenant.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    debut_demain = debut_jour + timedelta(days=1)

    ventes_du_jour = db.scalar(
        select(func.coalesce(func.sum(Order.amount), 0)).where(
            func.lower(Order.status) == "completed",
            func.upper(Order.currency) == "HTG",
            Order.created_at >= debut_jour,
            Order.created_at < debut_demain,
        )
    ) or Decimal("0.00")

    # 3. Nombre de codes Wi-Fi disponibles
    codes_disponibles = db.scalar(
        select(func.count(WifiCode.id)).where(
            func.lower(WifiCode.status) == "available"
        )
    ) or 0

    # 4. Nombre de forfaits actifs
    plans_disponibles = db.scalar(
        select(func.count(Plan.id)).where(
            func.lower(Plan.status) == "active"
        )
    ) or 0

    return {
        "clients_inscrits": clients_inscrits,
        "ventes_du_jour": str(ventes_du_jour),
        "codes_disponibles": codes_disponibles,
        "plans_disponibles": plans_disponibles,
    }



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

        transaction = WalletTransaction(
            wallet_id=wallet.id,
            type="DEPOT",
            amount=data.amount,
            balance_after=wallet.balance,
            description="Recharge effectuée par un administrateur",
        )

        db.add(transaction)
        db.commit()
        db.refresh(wallet)

        return {
            "message": "Recharge effectuée avec succès",
            "user_id": user_id,
            "balance": wallet.balance,
            "currency": wallet.currency,
        }

    except Exception as exc:
        db.rollback()
        logger.exception("Erreur pendant la recharge du portefeuille")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la recharge : {str(exc)}",
        ) from exc




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



@router.get("/me/transactions")
def obtenir_mes_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    wallet = db.scalar(
        select(Wallet).where(Wallet.user_id == current_user.id)
    )

    if wallet is None:
        return []

    transactions = []

    # Recharges enregistrées dans le portefeuille
    recharges = (
        db.query(WalletTransaction)
        .filter(
            WalletTransaction.wallet_id == wallet.id,
            WalletTransaction.type == "DEPOT",
        )
        .all()
    )

    for recharge in recharges:
        transactions.append({
            "id": f"recharge-{recharge.id}",
            "type": "recharge",
            "description": recharge.description or "Recharge administrative",
            "amount": str(recharge.amount),
            "currency": wallet.currency,
            "date": recharge.created_at.isoformat(),
            "balance_after": str(recharge.balance_after),
        })

    # Achats de codes Wi-Fi
    achats = (
        db.query(Order, Plan)
        .join(Plan, Order.plan_id == Plan.id)
        .filter(
            Order.user_id == current_user.id,
            Order.status == "completed",
        )
        .all()
    )

    for commande, plan in achats:
        transactions.append({
            "id": f"achat-{commande.id}",
            "type": "achat_wifi",
            "description": f"Achat forfait Wi-Fi : {plan.name}",
            "amount": str(commande.amount),
            "currency": commande.currency,
            "date": commande.created_at.isoformat(),
            "balance_after": None,
        })

    transactions.sort(
        key=lambda transaction: transaction["date"],
        reverse=True,
    )

    return transactions