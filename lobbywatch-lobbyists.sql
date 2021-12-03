select distinct concat(vorname, ',', nachname)
from (
         select vorname, nachname
         from parlamentarier
         where now() between coalesce(ratsunterbruch_bis, im_rat_seit) and coalesce(im_rat_bis, now())
         union
         select vorname_kurz, nachname
         from parlamentarier
         where now() between coalesce(ratsunterbruch_bis, im_rat_seit) and coalesce(im_rat_bis, now())
           and vorname_kurz is not null
         union
         select 'Judith', 'Bellaïche'
         from parlamentarier
         where now() between coalesce(ratsunterbruch_bis, im_rat_seit) and coalesce(im_rat_bis, now())
           and id = 362
     ) personen
order by 1
;
