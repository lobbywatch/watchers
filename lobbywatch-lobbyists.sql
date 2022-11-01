select json_object(
   'id', person.id,
   'first', vorname,
   'middle', zweiter_vorname,
   'nick', vorname_kurz,
   'last', nachname,
   'citizenships', cast(concat('["', replace(buergerorte, ';', '","'), '"]') as json)
)
from person
join zutrittsberechtigung z on person.id = z.person_id
where now() between coalesce(z.von, now()) and coalesce(z.bis, now())
order by 1
;
