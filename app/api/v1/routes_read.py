from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas import ByIdsRequest, CartOut
from app.services.cart_service import CartService


router = APIRouter(prefix="/api/v1")


COOKIE_NAME = "sellio_cart"
COOKIE_MAX_AGE = int(timedelta(days=30).total_seconds())


def ensure_cookie(request: Request, response: Response) -> str:
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        cookie = secrets.token_urlsafe(24)
        response.set_cookie(
            key=COOKIE_NAME,
            value=cookie,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=COOKIE_MAX_AGE,
        )
    return cookie


@router.get("/cart/active", response_model=CartOut)
async def get_active(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    company_id: int,
    user_id: int | None = None,
):
    cookie = ensure_cookie(request, response)
    svc = CartService(session)
    cart = await svc.get_active(company_id=company_id, user_id=user_id, cookie=cookie)
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return await svc.serialize(cart)


@router.get("/cart/{cart_id}", response_model=CartOut)
async def get_cart(cart_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    svc = CartService(session)
    cart = await svc.get_cart(cart_id)
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return await svc.serialize(cart)


@router.get("/carts/by-user", response_model=list[CartOut])
async def carts_by_user(
    user_id: int,
    company_id: int | None = None,
    status_param: int | None = None,
    limit: int = 50,
    offset: int = 0,
    *,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    svc = CartService(session)
    carts = await svc.list_by_user(user_id, company_id, status_param, limit, offset)
    return [await svc.serialize(c) for c in carts]


@router.post("/carts/by-ids", response_model=list[CartOut])
async def carts_by_ids(body: ByIdsRequest, session: Annotated[AsyncSession, Depends(get_session)]):
    svc = CartService(session)
    carts = await svc.list_by_ids(body.ids)
    return [await svc.serialize(c) for c in carts]


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}


