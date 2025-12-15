from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session_ctx
from app.schemas import CartOut
from app.services.cart_service import CartService


router = APIRouter(prefix="/api/v1")


class UpsertCartRequest(BaseModel):
    company_id: int
    user_id: int | None = None
    cookie: str | None = None


class UpsertItemRequest(BaseModel):
    product_id: int
    name: str
    price: str
    quantity: int


class AddItemToCartRequest(BaseModel):
    company_id: int
    user_id: int | None = None
    cookie: str | None = None
    product_id: int
    name: str
    price: str
    quantity: int


class UpdateQuantityRequest(BaseModel):
    quantity: int


class ChangeStatusRequest(BaseModel):
    status: int


@router.post("/cart/upsert", response_model=CartOut, status_code=status.HTTP_201_CREATED)
async def upsert_cart(req: UpsertCartRequest):
    async with session_ctx() as session:
        svc = CartService(session)
        async with session.begin():
            cart = await svc.upsert_cart(
                company_id=req.company_id,
                user_id=req.user_id,
                cookie=req.cookie,
            )
            await session.refresh(cart)
        return await svc.serialize(cart)


@router.post("/cart/add-item", response_model=CartOut, status_code=status.HTTP_201_CREATED)
async def add_item_to_cart(req: AddItemToCartRequest):
    """Create cart if needed and add item in one operation"""
    async with session_ctx() as session:
        svc = CartService(session)
        async with session.begin():
            # Get or create active cart
            cart = await svc.upsert_cart(
                company_id=req.company_id,
                user_id=req.user_id,
                cookie=req.cookie,
            )
            # Add item to cart
            cart = await svc.upsert_item(
                cart_id=cart.id,
                product_id=req.product_id,
                name=req.name,
                price=req.price,
                quantity=req.quantity,
            )
            await session.refresh(cart)
        return await svc.serialize(cart)


@router.post("/cart/{cart_id}/item", response_model=CartOut)
async def upsert_item(cart_id: int, req: UpsertItemRequest):
    async with session_ctx() as session:
        svc = CartService(session)
        async with session.begin():
            cart = await svc.upsert_item(
                cart_id=cart_id,
                product_id=req.product_id,
                name=req.name,
                price=req.price,
                quantity=req.quantity,
            )
            if not cart:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
            await session.refresh(cart)
        return await svc.serialize(cart)


@router.put("/cart/{cart_id}/item/{product_id}/quantity")
async def update_quantity(cart_id: int, product_id: int, req: UpdateQuantityRequest):
    async with session_ctx() as session:
        svc = CartService(session)
        async with session.begin():
            cart = await svc.update_qty(cart_id, product_id, req.quantity)
            if not cart:
                # Cart was deleted (became empty) or not found
                return {"message": "Cart was deleted (became empty) or item not found", "cart_id": cart_id}
            await session.refresh(cart)
        return await svc.serialize(cart)


@router.delete("/cart/{cart_id}/item/{product_id}")
async def remove_item(cart_id: int, product_id: int):
    async with session_ctx() as session:
        svc = CartService(session)
        async with session.begin():
            cart = await svc.remove_item(cart_id, product_id)
            if not cart:
                # Cart was deleted (became empty) or not found
                return {"message": "Cart was deleted (became empty) or item not found", "cart_id": cart_id}
            await session.refresh(cart)
        return await svc.serialize(cart)


@router.put("/cart/{cart_id}/status", response_model=CartOut)
async def change_status(cart_id: int, req: ChangeStatusRequest):
    async with session_ctx() as session:
        svc = CartService(session)
        async with session.begin():
            cart = await svc.change_status(cart_id, req.status)
            if not cart:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown error")
            await session.refresh(cart)
        return await svc.serialize(cart)

