
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_admin
from app.db.dependencies import get_db
from app.modules.utilisateurs.model import User
from app.modules.plans_wifi.model import Plan, WifiCode
from app.modules.plans_wifi.schemas import (
    PlanCreate,
    PlanResponse,
    PlanUpdate,
    WifiCodeImport,
)

from app.modules.plans_wifi.schemas import WifiPurchaseRequest
from app.modules.plans_wifi.purchase_service import purchase_wifi_code
from sqlalchemy import func
from app.modules.plans_wifi.order_model import Order


router = APIRouter(prefix="/wifi", tags=["Wi-Fi"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]


@router.get("/plans", response_model=list[PlanResponse])
def lister_forfaits(db: DbSession):
    plans = (
        db.query(Plan)
        .filter(Plan.status == "active")
        .order_by(Plan.duration_hours.asc())
        .all()
    )

    stocks = (
        db.query(
            WifiCode.plan_id,
            func.count(WifiCode.id).label("total"),
        )
        .filter(WifiCode.status == "available")
        .group_by(WifiCode.plan_id)
        .all()
    )

    stock_par_forfait = {
        plan_id: total for plan_id, total in stocks
    }

    resultat = []

    for plan in plans:
        forfait = PlanResponse.model_validate(plan).model_dump()
        forfait["codes_available"] = stock_par_forfait.get(plan.id, 0)
        resultat.append(forfait)

    return resultat


@router.post(
    "/admin/plans",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def creer_forfait(
    data: PlanCreate,
    db: DbSession,
    admin: AdminUser,
):
    existe = (
        db.query(Plan)
        .filter(
            Plan.name == data.name,
            Plan.duration_hours == data.duration_hours,
        )
        .first()
    )

    if existe:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce forfait existe déjà pour cette durée.",
        )

    plan = Plan(**data.model_dump())
    db.add(plan)

    try:
        db.commit()
        db.refresh(plan)
    except Exception:
        db.rollback()
        raise

    return plan


@router.patch("/admin/plans/{plan_id}", response_model=PlanResponse)
def modifier_forfait(
    plan_id: int,
    data: PlanUpdate,
    db: DbSession,
    admin: AdminUser,
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Forfait introuvable.",
        )

    changements = data.model_dump(exclude_unset=True)

    for champ, valeur in changements.items():
        setattr(plan, champ, valeur)

    try:
        db.commit()
        db.refresh(plan)
    except Exception:
        db.rollback()
        raise

    return plan


@router.post(
    "/admin/codes/import",
    status_code=status.HTTP_201_CREATED,
)
def importer_codes(
    data: WifiCodeImport,
    db: DbSession,
    admin: AdminUser,
):
    plan = db.query(Plan).filter(Plan.id == data.plan_id).first()

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Forfait introuvable.",
        )

    codes = [code.strip() for code in data.codes]

    if any(not code for code in codes):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La liste contient un code vide.",
        )

    if len(codes) != len(set(codes)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La liste contient des codes en double.",
        )

    deja_presents = (
        db.query(WifiCode.code)
        .filter(WifiCode.code.in_(codes))
        .first()
    )

    if deja_presents:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Au moins un code existe déjà dans la base.",
        )

    db.add_all(
        [
            WifiCode(plan_id=data.plan_id, code=code)
            for code in codes
        ]
    )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"message": "Codes importés avec succès.", "total": len(codes)}





@router.get("/admin/codes")
def lister_tous_les_codes_wifi(
    db: DbSession,
    admin: AdminUser,
):
    codes = (
        db.query(WifiCode, Plan)
        .join(Plan, WifiCode.plan_id == Plan.id)
        .order_by(WifiCode.id.desc())
        .all()
    )

    return [
        {
            "id": code.id,
            "code": code.code,
            "status": code.status,
            "plan_id": code.plan_id,
            "plan_name": plan.name,
            "created_at": (
                code.imported_at.isoformat()
                if code.imported_at
                else None
            ),
        }
        for code, plan in codes
    ]




@router.post("/wifi/purchase")
def buy_wifi_code(
    data: WifiPurchaseRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    return purchase_wifi_code(
        db=db,
        user_id=current_user.id,
        plan_id=data.plan_id,
    )



@router.get("/my-codes")
def mes_codes_achetes(
    db: DbSession,
    current_user: CurrentUser,
):
    commandes = (
        db.query(Order, Plan, WifiCode)
        .join(Plan, Order.plan_id == Plan.id)
        .join(WifiCode, Order.wifi_code_id == WifiCode.id)
        .filter(
            Order.user_id == current_user.id,
            Order.status == "completed",
        )
        .order_by(Order.created_at.desc())
        .all()
    )

    return [
        {
            "order_id": commande.id,
            "plan_name": plan.name,
            "code": code.code,
            "amount": str(commande.amount),
            "currency": commande.currency,
            "purchased_at": commande.created_at,
        }
        for commande, plan, code in commandes
    ]
