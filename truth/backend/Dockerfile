FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# The register shares the document store access, the settings and the error handling of the platform, so the
# packages come along with it. The other services do not, and are left out.
COPY pyproject.toml uv.lock ./
COPY packages ./packages
COPY services ./services
COPY truth/backend ./truth/backend

RUN uv sync --package truth-service --no-dev

EXPOSE 8000

CMD ["uvicorn", "truth_service.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
