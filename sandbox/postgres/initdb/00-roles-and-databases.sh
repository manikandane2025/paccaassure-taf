#!/bin/sh
# Roles and databases for the Northwind Health sandbox. Runs once, on an empty data volume.
#   northwind_app  owns the northwind database (the API connects as this role)
#   northwind_ro   read-only access to northwind app data (Phase 4 DB scenarios)
#   pataf_history  owns the pataf_history database (history store, Phase 5 migrations)
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v app_pw="$NWH_DB_APP_PASSWORD" \
  -v ro_pw="$NWH_DB_READONLY_PASSWORD" \
  -v history_pw="$NWH_DB_HISTORY_PASSWORD" <<'SQL'
CREATE ROLE northwind_app LOGIN PASSWORD :'app_pw';
CREATE ROLE northwind_ro LOGIN PASSWORD :'ro_pw';
CREATE ROLE pataf_history LOGIN PASSWORD :'history_pw';

ALTER DATABASE northwind OWNER TO northwind_app;
ALTER SCHEMA public OWNER TO northwind_app;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
GRANT CONNECT ON DATABASE northwind TO northwind_ro;
GRANT USAGE ON SCHEMA public TO northwind_ro;

CREATE DATABASE pataf_history OWNER pataf_history;
REVOKE ALL ON DATABASE pataf_history FROM PUBLIC;
GRANT CONNECT ON DATABASE pataf_history TO pataf_history;
SQL
