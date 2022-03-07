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

    cursor.execute("delete from sheets_query where query_set = 'recherche'")
    cursor.execute('''insert into sheets_query(query_set, sheet_name, query)
        values(%s, %s, %s)''',
                   ('recherche', 'IB in Recherche', '''
            select  null as cms_link,
                    p.vorname,
                    p.nachname,
                    m.company_name organisation,
                    concat('=hyperlink("', reg_company_url, '";"', m.uid, '")') as uid,
                    concat('=hyperlink("', publ_url, '";', publ_id, ')') as publikation,
                    date_format(journal_date, '%d.%m.%Y') as journal_datum,
                    label as rubrik,
                    extract as auszug
            from shab_name_match m
             join parlamentarier p on m.parlamentarier_id = p.id
             left join organisation o on o.uid = m.uid collate utf8mb4_unicode_ci
             where m.job_id = (select max(id) from shab_match_job)
              and p.im_rat_bis is null
              and not exists (
                  select null
                  from interessenbindung ib
                  where ib.parlamentarier_id = p.id
                    and ib.organisation_id = o.id
                 )
            order by publ_id desc
                   '''))
    cursor.execute('''insert into sheets_query(query_set, sheet_name, query)
        values(%s, %s, %s)''',
                   ('recherche', 'Mandate in Recherche', '''
            select  null as cms_link,
                    p.vorname,
                    p.nachname,
                    m.company_name organisation,
                    concat('=hyperlink("', reg_company_url, '";"', m.uid, '")') as uid,
                    concat('=hyperlink("', publ_url, '";', publ_id, ')') as publikation,
                    date_format(journal_date, '%d.%m.%Y') as journal_datum,
                    label as rubrik,
                    extract as auszug
            from shab_name_match m
             join person p on m.person_id = p.id
             left join organisation o on o.uid = m.uid collate utf8mb4_unicode_ci
             join zutrittsberechtigung z on p.id = z.person_id
             join parlamentarier p2 on z.parlamentarier_id = p2.id
             where m.job_id = (select max(id) from shab_match_job)
              and z.bis is null
              and p2.im_rat_bis is null
              and not exists (
                  select null
                  from mandat m
                  where m.person_id = p.id
                    and m.organisation_id = o.id
                 )
            order by publ_id desc
                   '''))
