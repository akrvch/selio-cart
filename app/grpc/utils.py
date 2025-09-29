from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Tuple


def ensure_generated() -> Tuple[object, object]:
    try:
        cart_pb2 = importlib.import_module("app.grpc.generated.cart_pb2")
        cart_pb2_grpc = importlib.import_module("app.grpc.generated.cart_pb2_grpc")
        return cart_pb2, cart_pb2_grpc
    except Exception:
        pass

    # Try to generate with grpc_tools.protoc
    from grpc_tools import protoc  # type: ignore

    proto_path = Path(__file__).parent / "protos" / "cart.proto"
    out_dir = Path(__file__).parent / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    args = [
        "protoc",
        f"-I{proto_path.parent}",
        f"--python_out={out_dir}",
        f"--grpc_python_out={out_dir}",
        str(proto_path),
    ]
    protoc.main(args)

    cart_pb2 = importlib.import_module("app.grpc.generated.cart_pb2")
    cart_pb2_grpc = importlib.import_module("app.grpc.generated.cart_pb2_grpc")
    return cart_pb2, cart_pb2_grpc


