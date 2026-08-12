FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml ./
COPY packages ./packages
COPY services ./services

RUN uv sync --package events-service --no-dev

EXPOSE 8000

CMD ["uvicorn", "events_service.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
