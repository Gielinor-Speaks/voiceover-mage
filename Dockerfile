# 🧙‍♂️ Voiceover Mage - Multi-stage Docker build
FROM python:3.13-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y \
    git curl build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY . .
RUN chown -R app:app /app

ENV PYTHONPATH=/app/src PYTHONUNBUFFERED=1 UV_LINK_MODE=copy

# 🔧 Development - Interactive shell with full tooling
FROM base AS dev
RUN apt-get update && apt-get install -y vim less sudo \
    && rm -rf /var/lib/apt/lists/* \
    && echo "app ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen \
    && chown -R app:app /app/.venv
USER app
CMD ["bash"]

# 🚀 Production - Lean runtime with only essentials  
FROM base AS prod
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev
USER app
EXPOSE 8000
CMD ["uv", "run", "app"]