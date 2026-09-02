
FROM python:3.14-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev


FROM python:3.14-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

# Aplikacja
COPY app.py router.py config.py .

ENV PATH="/app/.venv/bin:$PATH"

CMD ["fastapi", "run", "app.py"]
