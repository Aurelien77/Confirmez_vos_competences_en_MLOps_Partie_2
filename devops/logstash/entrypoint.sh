#!/bin/sh
set -e

JAR_PATH="/usr/share/logstash/logstash-core/lib/jars/postgresql.jar"

if [ ! -f "$JAR_PATH" ]; then
  echo "Téléchargement du driver PostgreSQL..."
  curl -L -o "$JAR_PATH" https://jdbc.postgresql.org/download/postgresql-42.7.4.jar
fi

exec logstash