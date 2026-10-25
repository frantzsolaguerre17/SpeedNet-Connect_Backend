

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UtilisateurCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=5, max_length=30)
    password: str = Field(min_length=8, max_length=128)


class UtilisateurResponse(BaseModel):
    id: int
    full_name: str
    phone: str
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



class UserLogin(BaseModel):
    phone: str = Field(min_length=5, max_length=30)
    password: str = Field(min_length=8, max_length=128)



class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UtilisateurResponse
