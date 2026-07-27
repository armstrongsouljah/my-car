#!/bin/sh
set -e

# Only run migrations + seed when starting the web server.
# Celery workers/beat share this image but must not race to migrate.
if [ -z "$1" ]; then
    echo "Applying migrations..."
    python manage.py migrate --no-input

    echo "Seeding super admin..."
    python manage.py seed_admin

    echo "Starting Gunicorn on port ${PORT:-8001}..."
    # --no-control-socket: appuser is a Debian system account with
    # HOME=/nonexistent, so gunicorn's control socket (which defaults to
    # $HOME/.gunicorn/) can't create its directory there. We don't use the
    # gunicornc control CLI, so just disable the socket instead of giving
    # appuser a writable home dir for a feature that's otherwise unused.
    exec gunicorn config.wsgi:application \
        --bind "0.0.0.0:${PORT:-8001}" \
        --workers 1 \
        --threads 8 \
        --timeout 0 \
        --no-control-socket
else
    exec "$@"
fi
