
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field
from app.modules.plans_wifi.order_model import Order

class PlanBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    duration_hours: int = Field(gt=0)
    price: Decimal = Field(ge=0)
    currency: str = Field(default="HTG", min_length=3, max_length=3)
    description: str | None = None


class PlanCreate(PlanBase):
    pass


class PlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    duration_hours: int | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    description: str | None = None
    status: str | None = None


class PlanResponse(PlanBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    codes_available: int = 0


class WifiCodeImport(BaseModel):
    plan_id: int = Field(gt=0)
    codes: list[str] = Field(min_length=1)


class WifiCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    status: str
    imported_at: datetime
    sold_at: datetime | None = None



class WifiPurchaseRequest(BaseModel):
    plan_id: int = Field(gt=0)
