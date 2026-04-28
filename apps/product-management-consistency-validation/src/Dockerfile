# Generated for product-management-consistency-validation
# Build context: repo root (.)
ARG PYTHON_VERSION=3.13-slim
ARG APP_UID=10001
ARG APP_GID=10001

# ── Stage 0: build the shared lib wheel from source ──
FROM python:${PYTHON_VERSION} AS lib-builder
RUN pip install --no-cache-dir uv
COPY lib/src /tmp/lib-src
WORKDIR /tmp/lib-src
RUN uv build --wheel --out-dir /tmp/lib-dist

# ── Stage 1: common base for dev and prod ──
FROM python:${PYTHON_VERSION} AS base
ARG APP_UID=10001
ARG APP_GID=10001
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_NAME=product-management-consistency-validation
RUN groupadd --gid ${APP_GID} appgroup && useradd --uid ${APP_UID} --gid ${APP_GID} --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser \
    && mkdir -p /app && chown -R appuser:appgroup /app
WORKDIR /app/src
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends build-essential libpq-dev git curl \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir --upgrade pip uv

# ── Stage 2: dev (editable, with test extras) ──
FROM base AS dev
ENV APP_ENV=dev
COPY apps/product-management-consistency-validation/src/pyproject.toml apps/product-management-consistency-validation/src/uv.lock ./
COPY apps/product-management-consistency-validation/src/ ./
ENV PYTHONPATH=/app/src
ENV PATH="/app/src/.venv/bin:$PATH"
RUN uv sync --frozen --all-extras
RUN chown -R appuser:appgroup /app
USER appuser
CMD ["uvicorn", "product_management_consistency_validation.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Stage 3: prod dependency layer ──
FROM base AS prod-builder
ENV APP_ENV=prod
COPY apps/product-management-consistency-validation/src/requirements.txt ./
RUN uv pip install --system --no-cache -r requirements.txt
# Install the lib wheel built in stage 0
COPY --from=lib-builder /tmp/lib-dist/holiday_peak_lib-*.whl /tmp/
RUN uv pip install --system --no-deps /tmp/holiday_peak_lib-*.whl \
    && rm -rf /tmp/*.whl
# Copy application code
COPY apps/product-management-consistency-validation/src/ ./
# Strip caches and tests from site-packages
RUN find /usr/local/lib -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
    find /usr/local/lib -name '*.pyc' -delete 2>/dev/null; \
    find /usr/local/lib -type d -name tests -path '*/site-packages/*' -exec rm -rf {} + 2>/dev/null; \
    true

# ── Stage 4: minimal production image ──
FROM python:${PYTHON_VERSION} AS prod
ARG APP_UID=10001
ARG APP_GID=10001
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
RUN groupadd --gid ${APP_GID} appgroup && useradd --uid ${APP_UID} --gid ${APP_GID} --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser \
    && mkdir -p /app && chown -R appuser:appgroup /app
WORKDIR /app/src
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=prod-builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=prod-builder --chown=appuser:appgroup /app/src /app/src
COPY --chown=appuser:appgroup apps/product-management-consistency-validation/prompts/ /app/apps/product-management-consistency-validation/prompts/
ENV WEB_CONCURRENCY=2
USER appuser
CMD ["sh", "-c", "python -m uvicorn product_management_consistency_validation.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-4}"]
