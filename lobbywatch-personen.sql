select distinct concat(vorname, ',', nachname)
from (
         select vorname, nachname
         from parlamentarier
         where now() between coalesce(ratsunterbruch_bis, im_rat_seit) and coalesce(im_rat_bis, now())
         union
         select 'Judith', 'Bellaïche'
         from parlamentarier
         where now() between coalesce(ratsunterbruch_bis, im_rat_seit) and coalesce(im_rat_bis, now())
           and id = 362
         union
         select vorname, nachname
         from person
                  join zutrittsberechtigung z on person.id = z.person_id
         where now() between coalesce(z.von, now()) and coalesce(z.bis, now())
     ) personen
order by 1
