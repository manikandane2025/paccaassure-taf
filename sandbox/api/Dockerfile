# Northwind Health sandbox API image (never shipped). Locked dependencies from uv.lock.
FROM ghcr.io/astral-sh/uv:0.12.18 AS uv

FROM python:3.12-slim
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY northwind_api ./northwind_api
RUN useradd --system --uid 10001 northwind
USER northwind
EXPOSE 8000
CMD ["uvicorn", "northwind_api.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
