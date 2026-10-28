

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

class AdminUtilisateurPortefeuilleResponse(UtilisateurResponse):
    balance: Decimal = Decimal("0.00")
    currency: str = "HTG"


class TransferRequest(BaseModel):
    phone: str = Field(min_length=1, max_length=30)
    amount: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )


class TransferResponse(BaseModel):
    message: str
    recipient_phone: str
    amount: Decimal
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


@router.get(
    "/admin/users",
    response_model=list[AdminUtilisateurPortefeuilleResponse],
)
def admin_list_users(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    utilisateurs = db.scalars(select(User)).all()

    portefeuilles = db.scalars(select(Wallet)).all()

    portefeuilles_par_user = {
        portefeuille.user_id: portefeuille
        for portefeuille in portefeuilles
    }

    resultat = []

    for utilisateur in utilisateurs:
        portefeuille = portefeuilles_par_user.get(utilisateur.id)

        donnees = UtilisateurResponse.model_validate(
            utilisateur,
            from_attributes=True,
        ).model_dump()

        donnees["balance"] = (
            portefeuille.balance
            if portefeuille is not None
            else Decimal("0.00")
        )

        donnees["currency"] = (
            portefeuille.currency
            if portefeuille is not None
            else "HTG"
        )

        resultat.append(donnees)

    return resultat


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


    
@router.get("/admin/transactions/recentes")
def admin_transactions_recentes(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    transactions = []

    # 1. Recharges et transferts des portefeuilles
    operations_wallet = (
        db.query(WalletTransaction, Wallet, User)
        .join(Wallet, WalletTransaction.wallet_id == Wallet.id)
        .join(User, Wallet.user_id == User.id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(50)
        .all()
    )

    for operation, wallet, client in operations_wallet:
        type_transaction = {
            "DEPOT": "recharge",
            "TRANSFER_OUT": "transfer_out",
            "TRANSFER_IN": "transfer_in",
        }.get(operation.type, operation.type.lower())

        transactions.append({
            "id": f"wallet-{operation.id}",
            "type": type_transaction,
            "description": (
                operation.description or "Opération de portefeuille"
            ),
            "amount": str(operation.amount),
            "currency": wallet.currency,
            "date": operation.created_at.isoformat(),
            "balance_after": str(operation.balance_after),
            "user_name": client.full_name,
            "user_phone": client.phone,
        })

    # 2. Achats de forfaits Wi-Fi confirmés
    achats_wifi = (
        db.query(Order, Plan, User)
        .join(Plan, Order.plan_id == Plan.id)
        .join(User, Order.user_id == User.id)
        .filter(func.lower(Order.status) == "completed")
        .order_by(Order.created_at.desc())
        .limit(50)
        .all()
    )

    for commande, plan, client in achats_wifi:
        transactions.append({
            "id": f"achat-{commande.id}",
            "type": "achat_wifi",
            "description": f"Achat forfait Wi-Fi : {plan.name}",
            "amount": str(commande.amount),
            "currency": commande.currency,
            "date": commande.created_at.isoformat(),
            "balance_after": None,
            "user_name": client.full_name,
            "user_phone": client.phone,
        })

    # 3. Trier toutes les opérations et garder les 10 plus récentes
    transactions.sort(
        key=lambda transaction: transaction["date"],
        reverse=True,
    )

    return transactions[:10]




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

    # 1. Recharges enregistrées dans le portefeuille
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
            "description": (
                recharge.description or "Recharge administrative"
            ),
            "amount": str(recharge.amount),
            "currency": wallet.currency,
            "date": recharge.created_at.isoformat(),
            "balance_after": str(recharge.balance_after),
        })

    # 2. Achats de codes Wi-Fi
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

    # 3. Transferts envoyés et reçus
    transferts = (
        db.query(WalletTransaction)
        .filter(
            WalletTransaction.wallet_id == wallet.id,
            WalletTransaction.type.in_([
                "TRANSFER_OUT",
                "TRANSFER_IN",
            ]),
        )
        .all()
    )

    for transfert in transferts:
        est_envoi = transfert.type == "TRANSFER_OUT"

        transactions.append({
            "id": f"transfert-{transfert.id}",
            "type": (
                "transfer_out" if est_envoi else "transfer_in"
            ),
            "description": (
                transfert.description
                or (
                    "Transfert envoyé"
                    if est_envoi
                    else "Transfert reçu"
                )
            ),
            "amount": str(transfert.amount),
            "currency": wallet.currency,
            "date": transfert.created_at.isoformat(),
            "balance_after": str(transfert.balance_after),
        })

    # 4. Trier du plus récent au plus ancien
    transactions.sort(
        key=lambda transaction: transaction["date"],
        reverse=True,
    )

    return transactions




    
@router.post(
    "/me/transfer",
    response_model=TransferResponse,
    status_code=status.HTTP_200_OK,
)
def transferer_argent(
    data: TransferRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    recipient_phone = data.phone.strip()

    if not recipient_phone:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le numéro du destinataire est obligatoire.",
        )

    if data.amount <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le montant doit être supérieur à zéro.",
        )

    try:
        # 1. Retrouver le destinataire par son numéro
        recipient = db.scalar(
            select(User).where(User.phone == recipient_phone)
        )

        if recipient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun utilisateur trouvé avec ce numéro.",
            )

        if recipient.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tu ne peux pas transférer de l'argent à toi-même.",
            )

        # 2. Verrouiller les deux portefeuilles dans le même ordre
        user_ids = sorted([current_user.id, recipient.id])

        wallets = db.scalars(
            select(Wallet)
            .where(Wallet.user_id.in_(user_ids))
            .order_by(Wallet.id)
            .with_for_update()
        ).all()

        wallets_by_user = {wallet.user_id: wallet for wallet in wallets}

        sender_wallet = wallets_by_user.get(current_user.id)
        recipient_wallet = wallets_by_user.get(recipient.id)

        if sender_wallet is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ton portefeuille est introuvable.",
            )

        if recipient_wallet is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Le destinataire n'a pas de portefeuille.",
            )

        # 3. Vérifier la devise et le solde
        if sender_wallet.currency != recipient_wallet.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Les deux portefeuilles doivent utiliser la même devise.",
            )

        if sender_wallet.balance < data.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solde insuffisant pour effectuer ce transfert.",
            )

        # 4. Débiter l'expéditeur et créditer le destinataire
        sender_wallet.balance -= data.amount
        recipient_wallet.balance += data.amount

        # 5. Enregistrer les deux opérations
        db.add_all([
            WalletTransaction(
                wallet_id=sender_wallet.id,
                type="TRANSFER_OUT",
                amount=data.amount,
                balance_after=sender_wallet.balance,
                description=(
                    f"Transfert envoyé au numéro {recipient.phone}"
                ),
            ),
            WalletTransaction(
                wallet_id=recipient_wallet.id,
                type="TRANSFER_IN",
                amount=data.amount,
                balance_after=recipient_wallet.balance,
                description=(
                    f"Transfert reçu du numéro {current_user.phone}"
                ),
            ),
        ])

        # Les deux soldes et les transactions sont validés ensemble.
        db.commit()
        db.refresh(sender_wallet)

        return {
            "message": "Transfert effectué avec succès.",
            "recipient_phone": recipient.phone,
            "amount": data.amount,
            "balance": sender_wallet.balance,
            "currency": sender_wallet.currency,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()
        logger.exception("Erreur pendant le transfert entre utilisateurs")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Une erreur est survenue pendant le transfert.",
        ) from exc
