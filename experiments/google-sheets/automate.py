#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import mysql.connector
from dotenv import dotenv_values

from save_to_spreadsheet import authenticate, create_tab, write_data

config = {**dotenv_values(".env"), **os.environ}


def get_sheet_name():
    # now = datetime.datetime.now()
    # today = now.strftime("%d %b %Y")
    # return today
    return "Mandate zum terminieren"


def getData():
    sh_db = mysql.connector.connect(
        host=config["DB_HOST"],
        database="lobbywatch_public",
        user=config['DB_USER'],
        password=config['DB_PASSWORD'],
        use_unicode=True
    )

    db_cursor = sh_db.cursor()
    db_cursor.execute(f"""
        select  concat('=hyperlink("https://cms.lobbywatch.ch/bearbeitung/mandat.php?operation=view&pk0=', mandat.id, '";', publ_id, ')') mandat,
                p.vorname,
                p.nachname,
                m.company_name organisation,
                concat('=hyperlink("', reg_company_url, '";"', m.uid, '")') uid,
                concat('=hyperlink("', publ_url, '";', publ_id, ')') publikation,
                date_format(journal_date, '%d.%m.%Y') journal_datum,
                label aenderungstyp,
                extract auszug
        from shab_name_match m
         join person p on m.person_id = p.id
         join mandat on mandat.person_id = p.id
         join organisation o on mandat.organisation_id = o.id
         join zutrittsberechtigung z on p.id = z.person_id
         join parlamentarier p2 on z.parlamentarier_id = p2.id
        where label in ('Ausgeschiedene Personen und erloschene Unterschriften', 'Gelöschte Person', 'Persone dimissionarie e firme cancellate', 'Personne(s) et signature(s) radiée(s)')
          and job_id = (select max(id) from shab_match_job)
          and o.uid = m.uid collate utf8mb4_unicode_ci
          and mandat.bis is null
          and z.bis is null
          and p2.im_rat_bis is null
        order by publ_id desc
    """)

    data = [[d[0] for d in db_cursor.description]]
    data += db_cursor.fetchall()
    return data


def main():
    # TO-DO
    # Enter the ID of the Google Spreadsheet in which we are going to save the data
    # Make sure that the authenticated account has access to this Google Sheet
    SPREADSHEET_ID = "1e1zZCePlJjCmz1zEtU3y66sqkElcuD9pslI9OHowseg"
    SHEET_NAME = get_sheet_name()
    SERVICE = authenticate()
    DATA = getData()
    create_tab(SERVICE, SPREADSHEET_ID, SHEET_NAME)
    write_data(SERVICE, SPREADSHEET_ID, SHEET_NAME, DATA)


if __name__ == "__main__":
    main()
