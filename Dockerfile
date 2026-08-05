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
    AUREON_SOUNDFONT=/aureon/soundfonts/GeneralUser.sf2

WORKDIR /aureon

# System deps: fluidsynth for SoundFont rendering
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        fluidsynth \
        fluid-soundfont-gm \
        libsndfile1 \
        curl && \
    rm -rf /var/lib/apt/lists/*

# GeneralUser GS (the documented default SoundFont), pinned to a specific
# upstream commit. Its license (GeneralUser GS License v2.0) explicitly
# permits bundling in software projects; we keep the license text alongside.
# FluidR3_GM remains installed as a fallback via AUREON_SOUNDFONT override.
RUN mkdir -p /aureon/soundfonts && \
    curl -fsSL -o /aureon/soundfonts/GeneralUser.sf2 \
        "https://raw.githubusercontent.com/ad-si/GeneralUser/b9fdc98c358eeb6fb0b01f23de5eff87bfbb280b/GeneralUser.sf2" && \
    curl -fsSL -o /aureon/soundfonts/LICENSE.txt \
        "https://raw.githubusercontent.com/ad-si/GeneralUser/b9fdc98c358eeb6fb0b01f23de5eff87bfbb280b/LICENSE.txt"

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

# Non-root user (hardening): owns the output dir and runtime-writable paths.
# Fixed UID 1000 so bind-mounted files (./.env) are writable on hosts whose
# primary user is UID 1000 (the common desktop Linux case); Docker Desktop
# bind mounts are writable regardless of UID.
RUN groupadd -g 1000 aureon && useradd -u 1000 -g aureon -d /aureon aureon && \
    mkdir -p output && chown -R aureon:aureon /aureon

USER aureon

EXPOSE 8000

CMD ["python", "web/app.py"]
