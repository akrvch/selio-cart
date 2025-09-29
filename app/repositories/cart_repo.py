from __future__ import annotations

from typing import Iterable, Sequence

from sqlalchemy import Select, and_, delete, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Cart, CartItem, CartStatus


class CartRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, cart_id: int) -> Cart | None:
        stmt = select(Cart).where(Cart.id == cart_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_ids_ordered(self, ids: list[int]) -> list[Cart]:
        if not ids:
            return []
        order_mapping = {cart_id: idx for idx, cart_id in enumerate(ids)}
        stmt = select(Cart).where(Cart.id.in_(ids))
        res = await self.session.execute(stmt)
        carts = list(res.scalars().all())
        carts.sort(key=lambda c: order_mapping.get(c.id, 10**12))
        return carts

    async def list_by_user(self, user_id: int, company_id: int | None, status: int | None, limit: int, offset: int) -> list[Cart]:
        conditions = [Cart.user_id == user_id]
        if company_id and company_id > 0:
            conditions.append(Cart.company_id == company_id)
        if status and status > 0:
            conditions.append(Cart.status == status)
        stmt = select(Cart).where(and_(*conditions)).limit(limit).offset(offset).order_by(Cart.id.desc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_active(self, company_id: int, user_id: int | None, cookie: str | None) -> Cart | None:
        conditions = [Cart.company_id == company_id, Cart.status == CartStatus.ACTIVE.value]
        if user_id:
            conditions.append(Cart.user_id == user_id)
        else:
            conditions.append(Cart.cookie == cookie)
        stmt = select(Cart).where(and_(*conditions)).limit(1)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def upsert_cart(self, company_id: int, user_id: int | None, cookie: str | None) -> Cart:
        existing = await self.get_active(company_id=company_id, user_id=user_id, cookie=cookie)
        if existing:
            return existing
        cart = Cart(company_id=company_id, user_id=user_id, cookie=cookie, status=CartStatus.ACTIVE.value)
        self.session.add(cart)
        try:
            await self.session.flush()
            return cart
        except IntegrityError:
            await self.session.rollback()
            # Unique violation due to race; fetch existing ACTIVE
            existing = await self.get_active(company_id=company_id, user_id=user_id, cookie=cookie)
            if existing:
                return existing
            raise

    async def change_status(self, cart_id: int, new_status: int) -> Cart | None:
        cart = await self.get_by_id(cart_id)
        if not cart:
            return None
        cart.status = new_status
        await self.session.flush()
        return cart


class CartItemRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_item(self, cart_id: int, product_id: int, name: str, price: str, quantity: int) -> CartItem:
        stmt = select(CartItem).where(and_(CartItem.cart_id == cart_id, CartItem.product_id == product_id))
        res = await self.session.execute(stmt)
        item = res.scalar_one_or_none()
        if item:
            item.name = name
            item.price = price
            item.quantity = quantity
            await self.session.flush()
            return item
        item = CartItem(cart_id=cart_id, product_id=product_id, name=name, price=price, quantity=quantity)
        self.session.add(item)
        try:
            await self.session.flush()
            return item
        except IntegrityError:
            await self.session.rollback()
            # On conflict (cart_id, product_id) read current and update to exact quantity
            res = await self.session.execute(stmt)
            item = res.scalar_one()
            item.name = name
            item.price = price
            item.quantity = quantity
            await self.session.flush()
            return item

    async def update_quantity(self, cart_id: int, product_id: int, quantity: int) -> CartItem | None:
        stmt = select(CartItem).where(and_(CartItem.cart_id == cart_id, CartItem.product_id == product_id))
        res = await self.session.execute(stmt)
        item = res.scalar_one_or_none()
        if not item:
            return None
        item.quantity = quantity
        await self.session.flush()
        return item

    async def remove_item(self, cart_id: int, product_id: int) -> bool:
        stmt = delete(CartItem).where(and_(CartItem.cart_id == cart_id, CartItem.product_id == product_id))
        res = await self.session.execute(stmt)
        return res.rowcount and res.rowcount > 0


