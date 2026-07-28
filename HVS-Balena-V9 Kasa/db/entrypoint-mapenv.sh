#!/bin/bash
set -e

# En balena, docker-compose NO interpola ${DB_*}; MYSQL_* llega como literal
# "${DB_USER}" (o vacia). Derivamos MYSQL_* de DB_* (que balena si inyecta bien)
# cuando MYSQL_* falta o quedo sin interpolar. En dev, MYSQL_* ya viene resuelta
# por docker compose y no se toca.
needs_map() {
  case "$1" in
    ""|'${'*) return 0 ;;   # vacio o literal no interpolado "${...}"
    *)        return 1 ;;
  esac
}

if needs_map "${MYSQL_USER:-}"     && [ -n "${DB_USER:-}" ];     then export MYSQL_USER="$DB_USER";     fi
if needs_map "${MYSQL_PASSWORD:-}" && [ -n "${DB_PASSWORD:-}" ]; then export MYSQL_PASSWORD="$DB_PASSWORD"; fi
if needs_map "${MYSQL_DATABASE:-}" && [ -n "${DB_NAME:-}" ];     then export MYSQL_DATABASE="$DB_NAME";     fi

exec /usr/local/bin/docker-entrypoint.sh "$@"
