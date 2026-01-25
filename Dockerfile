# Multi-stage build following uv best practices
# Stage 1: Builder - install dependencies with uv
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --extra cli --locked --no-install-project

COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock
COPY README.md /app/README.md
COPY src /app/src
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --extra cli --locked


# Stage 2: Runtime - slim final image
FROM python:3.13-slim-bookworm

# Create non-root user for security
RUN groupadd --system --gid 999 alguerisme \
 && useradd --system --gid 999 --uid 999 --create-home alguerisme

# Copy application and virtual environment from builder
COPY --from=builder --chown=alguerisme:alguerisme /app /app

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Use non-root user
USER alguerisme

# Set working directory
WORKDIR /app

# Default command (can be overridden in docker-compose)
CMD ["alguerisme", "--help"]
