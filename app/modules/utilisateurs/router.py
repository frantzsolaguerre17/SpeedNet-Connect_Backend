
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.core.security import creer_access_token
from app.db.dependencies import get_db
from app.modules.utilisateurs import service
from app.modules.utilisateurs.model import User
from app.modules.utilisateurs.schema import (
    LoginResponse,
    UserLogin,
    UtilisateurCreate,
    UtilisateurResponse,
)


router = APIRouter(prefix="/users", tags=["Users"])


class AdminCreateUser(UtilisateurCreate):
    role: Literal["user", "admin"] = "user"


class AdminMessage(BaseModel):
    message: str


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
