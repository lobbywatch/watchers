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

    cursor.execute("delete from sheets_query where query_set = 'oligarchen'")
    cursor.execute('''insert into sheets_query(query_set, sheet_name, query)
        values(%s, %s, %s)''',
                   ('oligarchen', 'HR Einträge', '''
select  m.other_id as id,
        substr(extract, locate('👑', extract)+1, locate('👑', extract, locate('👑', extract)+2)-locate('👑', extract)-1) name,
        m.company_name organisation,
        concat('=hyperlink("', reg_company_url, '";"', m.uid, '")') as uid,
        concat('=hyperlink("', publ_url, '";', publ_id, ')') as publikation,
        date_format(journal_date, '%d.%m.%Y') as journal_datum,
        label as rubrik,
        extract as auszug
from shab_name_match m
where m.job_id = 36
order by publ_id desc
                   '''))
