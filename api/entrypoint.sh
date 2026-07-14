#!/bin/sh
set -e

# Only run migrations + seed when starting the web server.
# Celery workers/beat share this image but must not race to migrate.
if [ -z "$1" ]; then
    echo "Applying migrations..."
    python manage.py migrate --no-input

    echo "Seeding super admin..."
    python manage.py seed_admin

    echo "Starting Gunicorn on port ${PORT:-8000}..."
    exec gunicorn config.wsgi:application \
        --bind "0.0.0.0:${PORT:-8000}" \
        --workers 1 \
        --threads 8 \
        --timeout 0
else
    exec "$@"
fi
