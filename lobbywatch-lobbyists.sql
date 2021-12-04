select distinct concat(vorname, ',', nachname)
from (
         select case when zweiter_vorname is not null then concat(vorname, ' ', zweiter_vorname) else vorname end vorname, nachname
         from person
                  join zutrittsberechtigung z on person.id = z.person_id
         where now() between coalesce(z.von, now()) and coalesce(z.bis, now())
         union
         select vorname_kurz, nachname
         from person
                  join zutrittsberechtigung z on person.id = z.person_id
         where now() between coalesce(z.von, now()) and coalesce(z.bis, now())
           and vorname_kurz is not null
     ) personen
order by 1
;
