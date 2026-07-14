# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install uv from PyPI (avoids pulling ghcr.io/astral-sh/uv, which can be
# unreachable behind some networks/proxies).
RUN pip install --no-cache-dir uv

WORKDIR /app

# Install dependencies into a project venv managed by uv.
ENV UV_PROJECT_ENVIRONMENT=/venv \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project || uv sync --no-dev


# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/venv/bin:$PATH" \
    PORT=8001

WORKDIR /app

COPY --from=builder /venv /venv

COPY . .

# Collect static files at build time with a throw-away secret key.
# The real SECRET_KEY is injected at runtime via environment variable.
RUN SECRET_KEY=build-time-placeholder \
    DATABASE_URL=sqlite:////tmp/build.db \
    REDIS_URL=locmem \
    python manage.py collectstatic --noinput

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && \
    addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    mkdir -p /app/media && \
    chown -R appuser:appgroup /app /entrypoint.sh

USER appuser

EXPOSE ${PORT}

ENTRYPOINT ["/entrypoint.sh"]
