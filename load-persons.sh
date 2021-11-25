#!/bin/sh

docker exec -i postgres_docker_images_mysql_1 mysql --user=root --password=root --database=lobbywatch_public --default-character-set=UTF8MB4 < lobbywatch-personen.sql | tail -n +2 > personen.csv
