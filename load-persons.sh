#!/bin/bash

set -a; source .env; set +a

mysql --host=$DB_HOST --user=$DB_USER --password=$DB_PASSWORD --database=$DB_DATABASE --default-character-set=UTF8MB4 < lobbywatch-parliamentarians.sql | tail -n +2 > parliamentarians.ndjson
mysql --host=$DB_HOST --user=$DB_USER --password=$DB_PASSWORD --database=$DB_DATABASE --default-character-set=UTF8MB4 < lobbywatch-lobbyists.sql | tail -n +2 > lobbyists.ndjson
