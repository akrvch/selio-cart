PY?=python

.PHONY: dev run test proto-gen alembic-upgrade docker-build

dev:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

run:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8080

test:
	uv run pytest -q

proto-gen:
	uv run python -m grpc_tools.protoc -I app/grpc/protos --python_out=app/grpc/generated --grpc_python_out=app/grpc/generated app/grpc/protos/cart.proto

alembic-upgrade:
	uv run alembic upgrade head

docker-build:
	docker build -t sellio-cart:local .

compose-up:
	docker compose up --build

compose-down:
	docker compose down -v


