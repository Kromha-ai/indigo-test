# Catalog Service image. Ships the normalised catalogue (data/catalog.json), not the raw CSV.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY data/catalog.json ./data/catalog.json

RUN useradd --system --uid 10001 catalog
USER catalog

EXPOSE 8000
# One worker: the rate limiter is in memory. --proxy-headers: Caddy terminates TLS.
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
