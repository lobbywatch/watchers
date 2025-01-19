#!/bin/bash

set -a; source .env; set +a

parliamentarians_sql=$(cat <<EOF
select distinct json_object(
   'id', person.id,
   'first', vorname,
   'middle', case zweiter_vorname when '' then null else zweiter_vorname end,
   'nick', case vorname_kurz when '' then null else vorname_kurz end,
   'last', nachname,
   'citizenships', buergerorte
) json
from person
join zutrittsberechtigung z on person.id = z.person_id
where now() between coalesce(z.von, now()) and coalesce(z.bis, now())
order by person.id
;
EOF
)

lobbyists_sql=$(cat <<EOF
select distinct json_object(
   'id', person.id,
   'first', vorname,
   'middle', case zweiter_vorname when '' then null else zweiter_vorname end,
   'nick', case vorname_kurz when '' then null else vorname_kurz end,
   'last', nachname,
   'citizenships', buergerorte
) json
from person
join zutrittsberechtigung z on person.id = z.person_id
where now() between coalesce(z.von, now()) and coalesce(z.bis, now())
order by person.id
;
EOF
)

mysql --host=$DB_HOST --user=$DB_USER --password=$DB_PASSWORD --database=$DB_DATABASE --default-character-set=UTF8MB4 -e "$parliamentarians_sql" \
      | tail -n +2 \
      | jq -c '(.citizenships) |= if . == null then . else (tostring | gsub("\\\\t"; "") | split(";") | map(gsub("^\\s+|\\s+$"; ""))) end' \
      > parliamentarians.ndjson
mysql --host=$DB_HOST --user=$DB_USER --password=$DB_PASSWORD --database=$DB_DATABASE --default-character-set=UTF8MB4 -e "$lobbyists_sql" \
      | tail -n +2 \
      | jq -c '(.citizenships) |= if . == null then . else (tostring | gsub("\\\\t"; "") | split(";") | map(gsub("^\\s+|\\s+$"; ""))) end' \
      > lobbyists.ndjson
