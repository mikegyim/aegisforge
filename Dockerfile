# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.11

# ---- build stage -------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
COPY apps/api/pyproject.toml ./pyproject.toml
COPY apps/api/src ./src
RUN pip install --upgrade pip build && pip wheel --wheel-dir /wheels .

# ---- runtime stage -----------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AEGIS_ENVIRONMENT=prod \
    AEGIS_LOG_JSON=true

RUN groupadd --system aegis && \
    useradd --system --gid aegis --create-home --home-dir /home/aegis aegis

WORKDIR /app

COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

COPY simulation/digital_twin.yaml /app/simulation/digital_twin.yaml

USER aegis
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://127.0.0.1:8000/health').raise_for_status()"

CMD ["uvicorn", "aegisforge.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
