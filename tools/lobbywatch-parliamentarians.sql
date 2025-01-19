select json_object(
    'id', id,
    'first', vorname,
    'middle', case zweiter_vorname when '' then null else zweiter_vorname end,
    'nick', case vorname_kurz when '' then null else vorname_kurz end,
    'last', nachname,
    'citizenships', buergerorte
) json
from parlamentarier
where now() between coalesce(ratsunterbruch_bis, im_rat_seit) and coalesce(im_rat_bis, now())
order by id
;
