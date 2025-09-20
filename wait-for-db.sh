#!/bin/sh
# wait-for-db.sh

set -e

host="$1"
port="$2"
shift 2
cmd="$@"

until pg_isready -h "$host" -p "$port"; do
  echo "Ожидание PostgreSQL на $host:$port..."
  sleep 2
done

echo "PostgreSQL готов!"
exec $cmd