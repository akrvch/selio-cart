# Sellio Cart

Read-only REST + gRPC write microservice for Sellio multi-vendor marketplace.

## Tech
- Python 3.14
- FastAPI (REST read-only)
- gRPC (write/update/delete)
- SQLAlchemy 2.x (async), asyncpg, Alembic
- Dependency manager: uv
- Docker multi-stage, non-root
- Tests: pytest, pytest-asyncio, httpx
- Deploy: Helm chart in `helm/`

## Environment
- `DATABASE_URL` (single master)
- `HTTP_PORT` (default 8080)
- `GRPC_PORT` (default 50051)
- `APP_ENV` (e.g. local, dev, prod)

Example URLs:

```
DATABASE_URL=postgresql+asyncpg://user_cart:pass@postgresql-primary.sellio-infra.svc.cluster.local:5432/cart
```

## Local setup

Install uv and sync deps:

```bash
uv sync
```

Run REST (and embedded gRPC server):

```bash
make dev
```

Run migrations (connects to `DATABASE_URL`):

```bash
export DATABASE_URL="postgresql+asyncpg://user_cart:***@localhost:5432/cart"
uv run alembic upgrade head
```

Generate gRPC stubs (already included):

```bash
make proto-gen
```

Quickstart (local env without Docker):

```bash
export DATABASE_URL="postgresql+asyncpg://user_cart:pass@localhost:5432/cart"
uv run alembic upgrade head
make dev

## Docker Compose (local, external DB)

```bash
export DATABASE_URL="postgresql+asyncpg://user_cart:pass@your-remote-host:5432/cart"
docker compose up --build
```

This starts only the app (no local Postgres). The app runs Alembic migrations on start and exposes:
- REST: `http://localhost:8080`
- gRPC: `localhost:50051`

```

## REST (read-only)
- `GET /api/v1/cart/{cart_id}`
- `GET /api/v1/carts/by-user?user_id=&company_id=&status=&limit=&offset=`
- `POST /api/v1/carts/by-ids` body: `{ "ids": [1,2,3] }`
- `GET /api/v1/cart/active?company_id=` (cookie managed automatically)
- `GET /healthz`

## gRPC (write channel)
- See `app/grpc/protos/cart.proto` and `app/grpc/generated/`.
- Server listens on port 50051 inside the same process.

## Helm
- See `helm/` for chart, deployment, services, secret/config, and post-upgrade migration job.

## Notes
- All writes go through gRPC to primary DB. REST uses replica only and never writes.


