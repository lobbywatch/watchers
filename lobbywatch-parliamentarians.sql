select json_object(
    'id', id,
    'first', vorname,
    'middle', zweiter_vorname,
    'nick', vorname_kurz,
    'last', nachname,
    'citizenships', cast(concat('["', replace(buergerorte, ';', '","'), '"]') as json)
)
from parlamentarier
where now() between coalesce(ratsunterbruch_bis, im_rat_seit) and coalesce(im_rat_bis, now())
order by id
;
