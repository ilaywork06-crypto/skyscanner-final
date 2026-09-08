FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# The register shares the document store access, the settings and the error handling of the platform, so the
# libraries come along with it. The Skyscanner services do not - but the workspace has to be whole before it
# can be installed against its lockfile, so they are copied for that and nothing else.
COPY pyproject.toml uv.lock ./
COPY libraries ./libraries
COPY skyscanner/services ./skyscanner/services
COPY truth/backend ./truth/backend

RUN uv sync --package truth-service --no-dev

EXPOSE 8000

CMD ["uvicorn", "truth_service.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
