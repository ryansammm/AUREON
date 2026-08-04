# ── Stage 1: build React frontend ──────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app/web/frontend
COPY web/frontend/package.json web/frontend/package-lock.json ./
RUN npm ci
COPY web/frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ───────────────────────────────────
FROM python:3.11-slim AS runtime
LABEL maintainer="aureon"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AUREON_PORT=8000 \
    AUREON_HOST=0.0.0.0 \
    AUREON_SOUNDFONT=/usr/share/sounds/sf2/FluidR3_GM.sf2

WORKDIR /aureon

# System deps: fluidsynth for SoundFont rendering
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        fluidsynth \
        fluid-soundfont-gm \
        libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application source
COPY engine/        ./engine/
COPY tools/         ./tools/
COPY config/        ./config/
COPY web/app.py     ./web/app.py
COPY cli.py         ./
COPY pytest.ini     ./

# Built frontend from stage 1
COPY --from=frontend /app/web/frontend/dist/ ./web/frontend/dist/

# Output dir
RUN mkdir -p output

EXPOSE 8000

CMD ["python", "web/app.py"]
