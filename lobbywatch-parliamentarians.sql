select distinct concat(vorname, ',', nachname)
from (
         select case when zweiter_vorname is not null then concat(vorname, ' ', zweiter_vorname) else vorname end vorname, nachname
         from parlamentarier
         where now() between coalesce(ratsunterbruch_bis, im_rat_seit) and coalesce(im_rat_bis, now())
         union
         select vorname_kurz, nachname
         from parlamentarier
         where now() between coalesce(ratsunterbruch_bis, im_rat_seit) and coalesce(im_rat_bis, now())
           and vorname_kurz is not null
     ) personen
order by 1
;
