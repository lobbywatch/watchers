select json_object(
   'id', person.id,
   'first', vorname,
   'middle', case zweiter_vorname when '' then null else zweiter_vorname end,
   'nick', case vorname_kurz when '' then null else vorname_kurz end,
   'last', nachname,
   'citizenships', cast(concat('["', trim(regexp_replace(buergerorte, '\s*;\s*', '","')), '"]') as json)
) json
from person
join zutrittsberechtigung z on person.id = z.person_id
where now() between coalesce(z.von, now()) and coalesce(z.bis, now())
order by person.id
;

select length(trim(' a '))