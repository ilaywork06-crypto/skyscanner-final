FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# The workspace has to be whole before it can be installed against its lockfile, so every member of it
# is copied - the libraries, the sibling services, and the register that shares the libraries.
COPY pyproject.toml uv.lock ./
COPY libraries ./libraries
COPY skyscanner/services ./skyscanner/services
COPY truth/backend ./truth/backend

RUN uv sync --package storage-service --no-dev

EXPOSE 8001

CMD ["uvicorn", "storage_service.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8001"]
