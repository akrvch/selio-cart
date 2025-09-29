from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Cart, CartItem, CartStatus
from app.repositories.cart_repo import CartItemRepository, CartRepository


def compute_total(cart: Cart) -> str:
    total = Decimal("0.00")
    for item in cart.items:
        price = Decimal(str(item.price))
        total += price * item.quantity
    return f"{total:.2f}"


class CartService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.carts = CartRepository(session)
        self.items = CartItemRepository(session)

    async def serialize(self, cart: Cart) -> dict:
        return {
            "id": cart.id,
            "company_id": cart.company_id,
            "user_id": cart.user_id,
            "cookie": cart.cookie,
            "status": cart.status,
            "created_at": cart.created_at,
            "items": [
                {
                    "product_id": i.product_id,
                    "name": i.name,
                    "price": f"{Decimal(str(i.price)):.2f}",
                    "quantity": i.quantity,
                }
                for i in cart.items
            ],
            "total_amount": compute_total(cart),
        }

    async def get_cart(self, cart_id: int) -> Cart | None:
        return await self.carts.get_by_id(cart_id)

    async def list_by_user(self, user_id: int, company_id: int | None, status: int | None, limit: int, offset: int) -> list[Cart]:
        return await self.carts.list_by_user(user_id, company_id, status, limit, offset)

    async def list_by_ids(self, ids: list[int]) -> list[Cart]:
        return await self.carts.list_by_ids_ordered(ids)

    async def get_active(self, company_id: int, user_id: int | None, cookie: str | None) -> Cart | None:
        return await self.carts.get_active(company_id, user_id, cookie)

    # RW ops
    async def upsert_cart(self, company_id: int, user_id: int | None, cookie: str | None) -> Cart:
        return await self.carts.upsert_cart(company_id, user_id, cookie)

    async def upsert_item(self, cart_id: int, product_id: int, name: str, price: str, quantity: int) -> Cart | None:
        cart = await self.carts.get_by_id(cart_id)
        if not cart:
            return None
        await self.items.upsert_item(cart_id, product_id, name, price, quantity)
        await self.session.refresh(cart)
        return cart

    async def update_qty(self, cart_id: int, product_id: int, quantity: int) -> Cart | None:
        cart = await self.carts.get_by_id(cart_id)
        if not cart:
            return None
        await self.items.update_quantity(cart_id, product_id, quantity)
        await self.session.refresh(cart)
        return cart

    async def remove_item(self, cart_id: int, product_id: int) -> Cart | None:
        cart = await self.carts.get_by_id(cart_id)
        if not cart:
            return None
        await self.items.remove_item(cart_id, product_id)
        await self.session.refresh(cart)
        return cart

    async def change_status(self, cart_id: int, new_status: int) -> Cart | None:
        cart = await self.carts.get_by_id(cart_id)
        if not cart:
            return None
        # allowed transitions: ACTIVE -> LOCKED -> CHECKED_OUT or ACTIVE -> CANCELLED
        allowed = {
            CartStatus.ACTIVE.value: {CartStatus.LOCKED.value, CartStatus.CANCELLED.value},
            CartStatus.LOCKED.value: {CartStatus.CHECKED_OUT.value},
        }
        if cart.status not in allowed or new_status not in allowed[cart.status]:
            return None
        cart = await self.carts.change_status(cart_id, new_status)
        await self.session.refresh(cart)
        return cart


