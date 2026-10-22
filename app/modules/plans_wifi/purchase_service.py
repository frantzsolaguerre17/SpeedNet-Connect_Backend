
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.plans_wifi.model import Plan, WifiCode
from app.modules.plans_wifi.order_model import Order
from app.modules.wallets.model import Wallet
from app.modules.wallets.transaction_model import WalletTransaction


def purchase_wifi_code(
    db: Session,
    user_id: int,
    plan_id: int,
) -> dict:
    try:
        # 1. Verrouiller le portefeuille de l'utilisateur
        wallet = db.execute(
            select(Wallet)
            .where(Wallet.user_id == user_id)
            .with_for_update()
        ).scalar_one_or_none()

        if wallet is None:
            raise HTTPException(
                status_code=404,
                detail="Portefeuille introuvable",
            )

        # 2. Vérifier le forfait
        plan = db.execute(
            select(Plan).where(
                Plan.id == plan_id,
                Plan.status == "active",
            )
        ).scalar_one_or_none()

        if plan is None:
            raise HTTPException(
                status_code=404,
                detail="Forfait introuvable ou inactif",
            )

        if plan.currency.strip() != "HTG" or wallet.currency.strip() != "HTG":
            raise HTTPException(
                status_code=400,
                detail="La devise du forfait ou du portefeuille est invalide",
            )

        price = Decimal(str(plan.price))

        if price <= 0:
            raise HTTPException(
                status_code=400,
                detail="Le prix du forfait doit être supérieur à zéro",
            )

        # 3. Vérifier le solde
        if wallet.balance < price:
            raise HTTPException(
                status_code=400,
                detail="Solde insuffisant",
            )

        # 4. Réserver un code disponible avec verrouillage SQL
        wifi_code = db.execute(
            select(WifiCode)
            .where(
                WifiCode.plan_id == plan_id,
                WifiCode.status == "available",
            )
            .order_by(WifiCode.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()

        if wifi_code is None:
            raise HTTPException(
                status_code=409,
                detail="Aucun code disponible pour ce forfait",
            )

        # 5. Débiter le portefeuille et marquer le code comme vendu
        wallet.balance -= price
        wifi_code.status = "sold"
        wifi_code.sold_at = datetime.now(timezone.utc)

        # 6. Enregistrer la commande
        order = Order(
            user_id=user_id,
            plan_id=plan.id,
            wifi_code_id=wifi_code.id,
            amount=price,
            currency="HTG",
            status="completed",
        )
        db.add(order)
        db.flush()  # Génère order.id sans valider la transaction

        # 7. Enregistrer la transaction du portefeuille
        transaction = WalletTransaction(
            wallet_id=wallet.id,
            type="ACHAT",
            amount=price,
            balance_after=wallet.balance,
            order_id=order.id,
            description=f"Achat du forfait Wi-Fi : {plan.name}",
        )
        db.add(transaction)

        # 8. Valider toutes les opérations ensemble
        db.commit()

        # Le code n'est retourné qu'après la validation SQL
        return {
            "message": "Achat effectué avec succès",
            "order_id": order.id,
            "plan_name": plan.name,
            "amount": str(price),
            "currency": "HTG",
            "code": wifi_code.code,
            "balance_after": str(wallet.balance),
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de l'achat du code Wi-Fi",
        ) from None
