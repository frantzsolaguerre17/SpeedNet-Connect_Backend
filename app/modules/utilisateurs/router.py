

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.modules.utilisateurs import service
from app.modules.utilisateurs.schema import (
    UserLogin,
    UtilisateurCreate,
    UtilisateurResponse,
)

router = APIRouter(prefix="/users", tags=["Users"])


def get_db():
    if SessionLocal.kw.get("bind") is None:
        raise RuntimeError("Database is not configured")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/register",
    response_model=UtilisateurResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: UtilisateurCreate,
    db: Session = Depends(get_db),  # noqa: B008
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
    response_model=UtilisateurResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),  # noqa: B008
):
    try:
        return service.login_user(
            db=db,
            phone=credentials.phone,
            password=credentials.password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
