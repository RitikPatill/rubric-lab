FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency spec and sync (cached layer)
COPY pyproject.toml .
RUN uv sync --no-dev

# Copy source
COPY src ./src

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "rubriclab.main:app", "--host", "0.0.0.0", "--port", "8000"]
