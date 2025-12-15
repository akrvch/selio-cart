from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal

import grpc
from google.protobuf.empty_pb2 import Empty  # type: ignore

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session_ctx
from app.models import CartStatus
from app.services.cart_service import CartService
from .utils import ensure_generated
cart_pb2, cart_pb2_grpc = ensure_generated()


def serialize_cart_message(cart_dict: dict) -> cart_pb2.Cart:
    return cart_pb2.Cart(
        id=cart_dict["id"],
        company_id=cart_dict["company_id"],
        user_id=cart_dict["user_id"] or 0,
        cookie=cart_dict["cookie"] or "",
        status=cart_dict["status"],
        created_at=cart_dict["created_at"].isoformat(),
        items=[
            cart_pb2.CartItem(
                product_id=i["product_id"],
                name=i["name"],
                price=i["price"],
                quantity=i["quantity"],
            )
            for i in cart_dict["items"]
        ],
        total_amount=cart_dict["total_amount"],
    )


class CartServiceImpl(cart_pb2_grpc.CartServiceServicer):

    async def UpsertCart(self, request: cart_pb2.UpsertCartRequest, context: grpc.aio.ServicerContext) -> cart_pb2.CartResponse:  # type: ignore
        async with session_ctx() as session:
            svc = CartService(session)
            user_id = request.user_id or None
            cookie = request.cookie or None
            async with session.begin():
                cart = await svc.upsert_cart(company_id=request.company_id, user_id=user_id, cookie=cookie)
                await session.refresh(cart)
            serialized = await svc.serialize(cart)
            return cart_pb2.CartResponse(cart=serialize_cart_message(serialized))

    async def UpsertItem(self, request: cart_pb2.UpsertItemRequest, context: grpc.aio.ServicerContext) -> cart_pb2.CartResponse:  # type: ignore
        async with session_ctx() as session:
            svc = CartService(session)
            async with session.begin():
                cart = await svc.upsert_item(
                    cart_id=request.cart_id,
                    product_id=request.product_id,
                    name=request.name,
                    price=request.price,
                    quantity=request.quantity,
                )
                if not cart:
                    await context.abort(grpc.StatusCode.NOT_FOUND, "cart not found")
                await session.refresh(cart)
            serialized = await svc.serialize(cart)  # type: ignore[arg-type]
            return cart_pb2.CartResponse(cart=serialize_cart_message(serialized))

    async def UpdateQty(self, request: cart_pb2.UpdateQtyRequest, context: grpc.aio.ServicerContext) -> cart_pb2.CartResponse:  # type: ignore
        async with session_ctx() as session:
            svc = CartService(session)
            async with session.begin():
                cart = await svc.update_qty(request.cart_id, request.product_id, request.quantity)
                if not cart:
                    await context.abort(grpc.StatusCode.NOT_FOUND, "cart was deleted (became empty) or item not found")
                await session.refresh(cart)
            serialized = await svc.serialize(cart)  # type: ignore[arg-type]
            return cart_pb2.CartResponse(cart=serialize_cart_message(serialized))

    async def RemoveItem(self, request: cart_pb2.RemoveItemRequest, context: grpc.aio.ServicerContext) -> cart_pb2.CartResponse:  # type: ignore
        async with session_ctx() as session:
            svc = CartService(session)
            async with session.begin():
                cart = await svc.remove_item(request.cart_id, request.product_id)
                if not cart:
                    await context.abort(grpc.StatusCode.NOT_FOUND, "cart was deleted (became empty) or item not found")
                await session.refresh(cart)
            serialized = await svc.serialize(cart)  # type: ignore[arg-type]
            return cart_pb2.CartResponse(cart=serialize_cart_message(serialized))

    async def ChangeStatus(self, request: cart_pb2.ChangeStatusRequest, context: grpc.aio.ServicerContext) -> cart_pb2.CartResponse:  # type: ignore
        async with session_ctx() as session:
            svc = CartService(session)
            async with session.begin():
                cart = await svc.change_status(request.cart_id, request.status)
                if not cart:
                    await context.abort(grpc.StatusCode.FAILED_PRECONDITION, "invalid transition or cart not found")
                await session.refresh(cart)
            serialized = await svc.serialize(cart)  # type: ignore[arg-type]
            return cart_pb2.CartResponse(cart=serialize_cart_message(serialized))

    # RO
    async def GetCart(self, request: cart_pb2.GetCartRequest, context: grpc.aio.ServicerContext) -> cart_pb2.CartResponse:  # type: ignore
        async with session_ctx() as session:
            svc = CartService(session)
            cart = await svc.get_cart(request.cart_id)
            if not cart:
                await context.abort(grpc.StatusCode.NOT_FOUND, "not found")
            serialized = await svc.serialize(cart)  # type: ignore[arg-type]
            return cart_pb2.CartResponse(cart=serialize_cart_message(serialized))

    async def GetActiveCart(self, request: cart_pb2.GetActiveCartRequest, context: grpc.aio.ServicerContext) -> cart_pb2.CartResponse:  # type: ignore
        async with session_ctx() as session:
            svc = CartService(session)
            user_id = request.user_id or None
            cookie = request.cookie or None
            cart = await svc.get_active(company_id=request.company_id, user_id=user_id, cookie=cookie)
            if not cart:
                await context.abort(grpc.StatusCode.NOT_FOUND, "not found")
            serialized = await svc.serialize(cart)  # type: ignore[arg-type]
            return cart_pb2.CartResponse(cart=serialize_cart_message(serialized))

    async def ListByUser(self, request: cart_pb2.ListByUserRequest, context: grpc.aio.ServicerContext) -> cart_pb2.CartList:  # type: ignore
        async with session_ctx() as session:
            svc = CartService(session)
            company_id = request.company_id or None
            status_filter = request.status or None
            carts = await svc.list_by_user(request.user_id, company_id, status_filter, request.limit or 50, request.offset or 0)
            cart_msgs = [serialize_cart_message(await svc.serialize(c)) for c in carts]
            return cart_pb2.CartList(carts=cart_msgs)

    async def ListByIds(self, request: cart_pb2.ListByIdsRequest, context: grpc.aio.ServicerContext) -> cart_pb2.CartList:  # type: ignore
        async with session_ctx() as session:
            svc = CartService(session)
            carts = await svc.list_by_ids(list(request.ids))
            cart_msgs = [serialize_cart_message(await svc.serialize(c)) for c in carts]
            return cart_pb2.CartList(carts=cart_msgs)


async def serve_grpc(port: int) -> None:
    server = grpc.aio.server()
    cart_pb2_grpc.add_CartServiceServicer_to_server(CartServiceImpl(), server)
    server.add_insecure_port(f"0.0.0.0:{port}")
    await server.start()
    await server.wait_for_termination()


