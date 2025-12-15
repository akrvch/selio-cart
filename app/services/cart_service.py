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

    def _filter_empty_carts(self, carts: list[Cart]) -> list[Cart]:
        """Filter out carts without items"""
        return [c for c in carts if c.items]

    async def get_cart(self, cart_id: int) -> Cart | None:
        cart = await self.carts.get_by_id(cart_id)
        if cart and not cart.items:
            return None  # Don't return empty carts
        return cart

    async def list_by_user(self, user_id: int, company_id: int | None, status: int | None, limit: int, offset: int) -> list[Cart]:
        carts = await self.carts.list_by_user(user_id, company_id, status, limit, offset)
        return self._filter_empty_carts(carts)

    async def list_by_ids(self, ids: list[int]) -> list[Cart]:
        carts = await self.carts.list_by_ids_ordered(ids)
        return self._filter_empty_carts(carts)

    async def get_active(self, company_id: int, user_id: int | None, cookie: str | None) -> Cart | None:
        cart = await self.carts.get_active(company_id, user_id, cookie)
        if cart and not cart.items:
            return None  # Don't return empty carts
        return cart

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
        if quantity <= 0:
            # If quantity is 0 or negative, remove the item
            item_removed, cart_deleted = await self.items.remove_item(cart_id, product_id)
            if cart_deleted:
                return None  # Cart was deleted because it became empty
            if item_removed:
                await self.session.refresh(cart)
                return cart if cart.items else None
            return None
        await self.items.update_quantity(cart_id, product_id, quantity)
        await self.session.refresh(cart)
        return cart

    async def remove_item(self, cart_id: int, product_id: int) -> Cart | None:
        cart = await self.carts.get_by_id(cart_id)
        if not cart:
            return None
        item_removed, cart_deleted = await self.items.remove_item(cart_id, product_id)
        if not item_removed:
            return None
        if cart_deleted:
            return None  # Cart was deleted because it became empty
        await self.session.refresh(cart)
        return cart

    async def change_status(self, cart_id: int, new_status: int) -> Cart | None:
        cart = await self.carts.get_by_id(cart_id)
        if not cart:
            return None, "not_found"
        
        # Don't allow status change for empty carts
        if not cart.items:
            return None, "empty_cart"
        
        cart = await self.carts.change_status(cart_id, new_status)
        await self.session.refresh(cart)
        return cart


