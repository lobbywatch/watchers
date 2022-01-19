#!/bin/bash

set -a; source .env; set +a

mysql --user=$DB_USER --password=$DB_PASSWORD --database=lobbywatch_public --default-character-set=UTF8MB4 < lobbywatch-parliamentarians.sql | tail -n +2 > parliamentarians.csv
mysql --user=$DB_USER --password=$DB_PASSWORD --database=lobbywatch_public --default-character-set=UTF8MB4 < lobbywatch-lobbyists.sql | tail -n +2 > lobbyists.csv
