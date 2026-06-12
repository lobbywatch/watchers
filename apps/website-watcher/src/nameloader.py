import config
import json
from typing import List
import mariadb

from namematch.namematcher import Name, PersonType

parliamentarians_sql = """select json_object(
    'id', id,
    'first', vorname,
    'middle', case zweiter_vorname when '' then null else zweiter_vorname end,
    'nick', case vorname_kurz when '' then null else vorname_kurz end,
    'last', nachname,
    'citizenships', buergerorte
) json
from parlamentarier
where now() between coalesce(ratsunterbruch_bis, im_rat_seit) and coalesce(im_rat_bis, now())
order by id;
"""

lobbyists_sql = """select json_object(
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
order by person.id;
"""

conn_params = {
    "user": config.get_key("DB_USER"),
    "password": config.get_key("DB_PASSWORD"),
    "host": config.get_key("DB_HOST"),
    "database": config.get_key("DB_DATABASE"),
}
pool = mariadb.ConnectionPool(pool_name="myfirstpool", pool_size=3, **conn_params)


def get_names():
    conn = pool.get_connection()
    cursor = conn.cursor()
    # TODO this could probably be simplified further by using a UNION query
    names = _build_parliamentarian_cache(cursor)
    names.extend(_build_lobbyist_cache(cursor))
    cursor.close()
    conn.close()
    return names


def _build_parliamentarian_cache(cursor) -> List[Name]:
    cursor.execute(parliamentarians_sql)
    names = []
    for row in cursor.fetchall():
        names.append(
            json.loads(
                row[0],
                object_hook=lambda d: Name(
                    id=(PersonType.PARLIAMENTARIAN, d["id"]),
                    first=d["first"],
                    middle=tuple(d["middle"].split(" ")) if d["middle"] else None,
                    nick=d["nick"],
                    last=d["last"],
                    citizenships=None,
                ),
            )
        )
    return names


def _build_lobbyist_cache(cursor) -> List[Name]:
    cursor.execute(lobbyists_sql)
    names = []
    for row in cursor.fetchall():
        names.append(
            json.loads(
                row[0],
                object_hook=lambda d: Name(
                    id=(PersonType.LOBBYIST, d["id"]),
                    first=d["first"],
                    middle=tuple(d["middle"].split(" ")) if d["middle"] else None,
                    nick=d["nick"],
                    last=d["last"],
                    citizenships=None,
                ),
            )
        )
    return names
