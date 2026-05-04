#!/usr/bin/env sh
set -e

if [ "${DB_ENGINE:-postgres}" = "postgres" ]; then
  echo "Waiting for PostgreSQL at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
  until nc -z "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}"; do
    sleep 1
  done
fi

python manage.py migrate --noinput

if [ "${LOAD_INITIAL_DATA:-0}" = "1" ] && [ -f "${INITIAL_DATA_PATH:-/app/docker/seed/initial_data.json}" ]; then
  DATA_EXISTS="$(python manage.py shell -c "from django.contrib.auth import get_user_model; print('1' if get_user_model().objects.exists() else '0')" | tail -n 1)"
  if [ "$DATA_EXISTS" = "0" ]; then
    echo "Loading initial data from ${INITIAL_DATA_PATH:-/app/docker/seed/initial_data.json}..."
    python manage.py loaddata "${INITIAL_DATA_PATH:-/app/docker/seed/initial_data.json}"
  else
    echo "Initial data skipped: database already has users."
  fi
fi

exec "$@"
