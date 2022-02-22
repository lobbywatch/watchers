#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import mysql.connector
from dotenv import dotenv_values

config = {**dotenv_values(".env"), **os.environ}

if __name__ == "__main__":
    connection = mysql.connector.connect(
        host=config["DB_HOST"],
        database="lobbywatch_public",
        user=config['DB_USER'],
        password=config['DB_PASSWORD'],
        use_unicode=True
    )
    connection.autocommit = True
    cursor = connection.cursor()

    cursor.execute("delete from sheets_query where query_set = 'heidinews'")
    cursor.execute('''insert into sheets_query(query_set, sheet_name, query)
        values(%s, %s, %s)''',
                   ('heidinews', 'Interessenbindungen Gesundheitswesen FR', '''
select i.name_fr "groupe d'intérêt",
       concat('=hyperlink("', 'https://lobbywatch.ch/fr/daten/parlamentarier/', p.id, '";"', concat(p.vorname, ' ', p.nachname), '")') parlementaire,
       p.id parlementaire_id,
       coalesce(pp.abkuerzung_fr, pp.abkuerzung, '-') parti,
       k.abkuerzung canton,
       coalesce(p.beruf_fr, p.beruf, '-') profession,
       concat('=hyperlink("', 'https://lobbywatch.ch/fr/daten/organisation/', o.id, '";"', coalesce(o.name_fr, o.name_de), '")') organisation,
       o.id org_id,
       (select fr from translations t where context = 'organisation' and item = 'rechtsform' and de = o.rechtsform) "forme juridique",
       # date_format(coalesce(ib.von, ib.freigabe_datum), '%d.%m.%Y') "à partir de",
       date_format(ib.von, '%d.%m.%Y') "à partir de",
       (select fr from translations t where context = 'interessenbindung' and item = 'art' and de = ib.art) lien,
       (select fr from translations t where context = 'interessenbindung' and item = 'funktion_im_gremium' and de = ib.funktion_im_gremium) fonction,
       case when ibj.verguetung > 0 then 1 when ibj.verguetung = 0 then 0 else -1 end indémnités,
       IF(o.vernehmlassung IN ('immer', 'punktuell')
              AND ib.art IN ('geschaeftsfuehrend','vorstand')
              AND EXISTS (
                  SELECT in_kommission.kommission_id
                  FROM in_kommission in_kommission
                           LEFT JOIN branche branche
                                     ON (in_kommission.kommission_id = branche.kommission_id OR in_kommission.kommission_id = branche.kommission2_id)
                  WHERE (in_kommission.bis >= NOW() OR in_kommission.bis IS NULL)
                    AND in_kommission.parlamentarier_id = p.id
                    AND branche.id = i.branche_id), 'fort',
          IF(o.vernehmlassung IN ('immer', 'punktuell')
                 AND ib.art IN ('geschaeftsfuehrend','vorstand','taetig','beirat','finanziell'), 'moyen', 'faible')
           ) efficacité
from organisation o
         join (select * from interessengruppe where branche_id = 1) i on i.id in (o.interessengruppe_id, o.interessengruppe2_id, o.interessengruppe3_id)
         join interessenbindung ib on o.id = ib.organisation_id
         left join (select distinct interessenbindung_id, last_value(verguetung) over (partition by interessenbindung_id order by jahr rows between unbounded preceding and unbounded following) verguetung,
                                    last_value(jahr) over (partition by interessenbindung_id order by jahr rows between unbounded preceding and unbounded following) jahr
                    from interessenbindung_jahr) ibj on ib.id = ibj.interessenbindung_id
         join parlamentarier p on ib.parlamentarier_id = p.id
         left join partei pp on pp.id = p.partei_id
         join kanton k on p.kanton_id = k.id
where 1=1
  and o.rechtsform not in ('Parlamentarische Gruppe')
  and coalesce(p.im_rat_bis, now()) >= now()
  and coalesce(ib.bis, now()) >= now()
  and o.inaktiv = 0
  and ib.hauptberuflich = 0
order by 1, p.vorname, p.nachname, o.name_fr
                   '''))

    cursor.execute('''insert into sheets_query(query_set, sheet_name, query)
        values(%s, %s, %s)''',
                   ('heidinews', 'Interessenbindungen Gesundheitswesen DE', '''
select i.name "Lobbygruppe",
       concat('=hyperlink("', 'https://lobbywatch.ch/de/daten/parlamentarier/', p.id, '";"', concat(p.vorname, ' ', p.nachname), '")') Parlamentarier,
       p.id parlementarier_id,
       coalesce(pp.abkuerzung, '-') Partei,
       k.abkuerzung Kanton,
       coalesce(p.beruf, '-') Beruf,
       concat('=hyperlink("', 'https://lobbywatch.ch/de/daten/organisation/', o.id, '";"', coalesce(o.name_fr, o.name_de), '")') Organisation,
       o.id org_id,
       o.rechtsform "Rechtsform",
       # date_format(coalesce(ib.von, ib.freigabe_datum), '%d.%m.%Y') "à partir de",
       date_format(ib.von, '%d.%m.%Y') "Seit",
       ib.art Art,
       ib.funktion_im_gremium "Funktion",
       case when ibj.verguetung > 0 then 1 when ibj.verguetung = 0 then 0 else -1 end "Verguetung",
       IF(o.vernehmlassung IN ('immer', 'punktuell')
              AND ib.art IN ('geschaeftsfuehrend','vorstand')
              AND EXISTS (
                  SELECT in_kommission.kommission_id
                  FROM in_kommission in_kommission
                           LEFT JOIN branche branche
                                     ON (in_kommission.kommission_id = branche.kommission_id OR in_kommission.kommission_id = branche.kommission2_id)
                  WHERE (in_kommission.bis >= NOW() OR in_kommission.bis IS NULL)
                    AND in_kommission.parlamentarier_id = p.id
                    AND branche.id = i.branche_id), 'hoch',
          IF(o.vernehmlassung IN ('immer', 'punktuell')
                 AND ib.art IN ('geschaeftsfuehrend','vorstand','taetig','beirat','finanziell'), 'mittel', 'gering')
           ) Wirksamkeit
from organisation o
         join (select * from interessengruppe where branche_id = 1) i on i.id in (o.interessengruppe_id, o.interessengruppe2_id, o.interessengruppe3_id)
         join interessenbindung ib on o.id = ib.organisation_id
         left join (select distinct interessenbindung_id, last_value(verguetung) over (partition by interessenbindung_id order by jahr rows between unbounded preceding and unbounded following) verguetung,
                                    last_value(jahr) over (partition by interessenbindung_id order by jahr rows between unbounded preceding and unbounded following) jahr
                    from interessenbindung_jahr) ibj on ib.id = ibj.interessenbindung_id
         join parlamentarier p on ib.parlamentarier_id = p.id
         left join partei pp on pp.id = p.partei_id
         join kanton k on p.kanton_id = k.id
where 1=1
  and o.rechtsform not in ('Parlamentarische Gruppe')
  and coalesce(p.im_rat_bis, now()) >= now()
  and coalesce(ib.bis, now()) >= now()
  and o.inaktiv = 0
  and ib.hauptberuflich = 0
order by 1, p.vorname, p.nachname, o.name_fr
                   '''))
