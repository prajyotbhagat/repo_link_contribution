# ============================================================
# Build stage — install all Python dependencies
# ============================================================
FROM python:3.12-slim AS builder

WORKDIR /app

# System deps needed to compile some packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/base.txt
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements/base.txt

# ============================================================
# Runtime stage — lean final image
# ============================================================
FROM python:3.12-slim

WORKDIR /app

# Runtime system deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy project source
COPY . .

# Create non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Collect static files
RUN DJANGO_SETTINGS_MODULE=config.settings_prod \
    DJANGO_SECRET_KEY=dummy-build-secret \
    DATABASE_URL=sqlite:///dummy.db \
    python manage.py collectstatic --noinput || true

EXPOSE 8000

# Default: run gunicorn (overridden in docker-compose for worker/beat)
CMD ["gunicorn", "-c", "gunicorn.conf.py", "config.wsgi:application"]
