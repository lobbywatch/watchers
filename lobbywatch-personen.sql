select distinct concat(vorname, ',', nachname)
from (
         select vorname, nachname
         from parlamentarier
         where now() between coalesce(im_rat_seit, now()) and coalesce(im_rat_bis, now())
         union
         select vorname, nachname
         from person
                  join zutrittsberechtigung z on person.id = z.person_id
         where now() between coalesce(z.von, now()) and coalesce(z.bis, now())
     ) personen
order by 1
