# 🧙‍♂️ Voiceover Mage - Multi-stage Docker build
FROM python:3.13-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y \
    git curl build-essential ca-certificates locales \
    && sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY . .
RUN chown -R app:app /app

ENV PYTHONPATH=/app/src PYTHONUNBUFFERED=1 UV_LINK_MODE=copy \
    LANG=en_US.UTF-8 LANGUAGE=en_US:en LC_ALL=en_US.UTF-8

# 🔧 Development - Interactive shell with full tooling
FROM base AS dev
RUN apt-get update && apt-get install -y vim less sudo \
    wget curl ca-certificates fonts-liberation libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libatspi2.0-0 libcups2 libdrm2 libgtk-3-0 libgtk-4-1 \
    libnspr4 libnss3 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libxss1 fonts-unifont \
    && rm -rf /var/lib/apt/lists/* \
    && echo "app ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen \
    && chown -R app:app /app/.venv
USER app
RUN uv run playwright install chromium
CMD ["bash"]

# 🚀 Production - Lean runtime with only essentials  
FROM base AS prod
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev
USER app
EXPOSE 8000
CMD ["uv", "run", "app"]