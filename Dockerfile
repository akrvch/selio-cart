# syntax=docker/dockerfile:1.7

FROM python:3.14-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install uv (package manager)
RUN pip install --upgrade pip && pip install uv

WORKDIR /app
COPY pyproject.toml .

FROM base AS builder
RUN useradd -u 10001 -m appuser
COPY . .
# Create a virtualenv using uv and install deps
RUN uv venv /opt/venv && . /opt/venv/bin/activate && uv pip install .[test]

FROM python:3.14-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN useradd -u 10001 -m appuser
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .

USER appuser
EXPOSE 8080 50051

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]


