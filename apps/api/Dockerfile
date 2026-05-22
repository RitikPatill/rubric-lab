FROM python:3.12-slim

# Install uv and curl (curl needed for healthcheck)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency spec and lockfile, sync (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy source
COPY src ./src

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "rubriclab.main:app", "--host", "0.0.0.0", "--port", "8000"]
