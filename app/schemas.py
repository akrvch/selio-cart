from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class CartItemOut(BaseModel):
    product_id: int
    name: str
    price: str
    quantity: int


class CartOut(BaseModel):
    id: int
    company_id: int
    user_id: int | None
    cookie: str | None
    status: int
    created_at: datetime
    items: list[CartItemOut]
    total_amount: str


class ByIdsRequest(BaseModel):
    ids: list[int]


