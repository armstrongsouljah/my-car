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

# WeasyPrint (monthly expense report PDFs, see #21) shells out to Pango/Cairo
# via GObject introspection rather than a pure-Python renderer, so these
# system libs are a hard runtime dependency, not just a build-time one — the
# same image also runs the Celery worker/beat pods that render the PDFs.
RUN apt-get update && apt-get install --no-install-recommends -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /venv /venv

COPY . .

# Collect static files at build time with throw-away config. The real
# values (SECRET_KEY, DEFAULT_FROM_EMAIL, etc.) are injected at runtime
# via environment variable — these are never actually used to send mail.
RUN SECRET_KEY=build-time-placeholder \
    DATABASE_URL=sqlite:////tmp/build.db \
    REDIS_URL=locmem \
    DEFAULT_FROM_EMAIL=build@example.com \
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
