#!/bin/sh

docker exec -i $(docker ps --filter "expose=3306" -q) mysql --user=root --password=root --database=lobbywatch_public --default-character-set=UTF8MB4 < lobbywatch-parliamentarians.sql | tail -n +2 > parliamentarians.csv
docker exec -i $(docker ps --filter "expose=3306" -q) mysql --user=root --password=root --database=lobbywatch_public --default-character-set=UTF8MB4 < lobbywatch-lobbyists.sql | tail -n +2 > lobbyists.csv
