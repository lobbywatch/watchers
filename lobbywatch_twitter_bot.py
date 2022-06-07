#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import urllib.parse
from collections import namedtuple
from pathlib import Path

import mysql.connector
import paramiko
import sys
import time
import tweepy
import unicodedata
from dotenv import dotenv_values
from slack_sdk import WebClient
from sshtunnel import SSHTunnelForwarder

config = {**dotenv_values("twitterbot.env"), **os.environ}

parser = argparse.ArgumentParser(description='Kommuniziert neu freigegebene Interessenbindungen als Post auf Twitter.')
parser.add_argument('--dry-run', action=argparse.BooleanOptionalAction)


Person = namedtuple('Person', 'geschlecht')
Interessenbindung = namedtuple('Interessenbindung', 'art funktion_im_gremium')
Organisation = namedtuple('Organisation', 'rechtsform')


def lobbywatch_bindungsart(pers, ib, org, lang):
    def translate(key):
        cursor.execute('''
            select t.translation
            from translation_source s
            join translation_target t on t.translation_source_id = s.id
            where source = ?
              and t.lang = ?
        ''', (key,lang))
        return cursor.fetchone()[0]

    def art():
        if ib.art in ('mitglied', 'geschaeftsfuehrend', 'vorstand', 'taetig', 'beirat', 'finanziell', 'gesellschafter'):
            return translate(ib.art)
        else:
            return ib.art.capitalize()

    def funktion_im_gremium():
        if ib.funktion_im_gremium == 'praesident' and pers.geschlecht == 'F':
            return translate('Präsidentin')
        elif ib.funktion_im_gremium == 'praesident' and pers.geschlecht == 'M':
            return translate('Präsident')
        elif ib.funktion_im_gremium == 'vizepraesident' and pers.geschlecht == 'F':
            return translate('Vizepräsidentin')
        elif ib.funktion_im_gremium == 'vizepraesident' and pers.geschlecht == 'M':
            return translate('Vizepräsident')
        elif ib.funktion_im_gremium == 'mitglied':
            return translate('Mitglied')
        else:
            return ib.funktion_im_gremium

    # Stiftung
    if org.rechtsform == 'Stiftung' and ib.art == 'vorstand' and ib.funktion_im_gremium == 'praesident' and pers.geschlecht == 'F':
        return translate('Stiftungsratspräsidentin')
    elif org.rechtsform == 'Stiftung' and ib.art == 'vorstand' and ib.funktion_im_gremium == 'praesident' and pers.geschlecht == 'M':
        return translate('Stiftungsratspräsident')
    elif org.rechtsform == 'Stiftung' and ib.art == 'vorstand' and ib.funktion_im_gremium == 'vizepraesident' and pers.geschlecht == 'F':
        return translate('Stiftungsratsvizepräsidentin')
    elif org.rechtsform == 'Stiftung' and ib.art == 'vorstand' and ib.funktion_im_gremium == 'vizepraesident' and pers.geschlecht == 'M':
        return translate('Stiftungsratsvizepräsident')
    elif org.rechtsform == 'Stiftung' and ib.art == 'vorstand' and pers.geschlecht == 'F':
        return translate('Stiftungsrätin')
    elif org.rechtsform == 'Stiftung' and ib.art == 'vorstand' and pers.geschlecht == 'M':
        return translate('Stiftungsrat')
    elif org.rechtsform == 'Stiftung' and ib.art == 'geschaeftsfuehrend' and ib.funktion_im_gremium == 'praesident' and pers.geschlecht == 'F':
        return translate('Geschäftsführerin')
    elif org.rechtsform == 'Stiftung' and ib.art == 'geschaeftsfuehrend' and ib.funktion_im_gremium == 'praesident' and pers.geschlecht == 'M':
        return translate('Geschäftsführer')
    elif org.rechtsform == 'Stiftung' and ib.art == 'geschaeftsfuehrend' and ib.funktion_im_gremium == 'vizepraesident' and pers.geschlecht == 'F':
        return translate('Vizegeschäftsführerin')
    elif org.rechtsform == 'Stiftung' and ib.art == 'geschaeftsfuehrend' and ib.funktion_im_gremium == 'vizepraesident' and pers.geschlecht == 'M':
        return translate('Vizegeschäftsführer')
    elif org.rechtsform == 'Stiftung' and ib.art == 'geschaeftsfuehrend' and pers.geschlecht == 'F':
        return translate('Geschäftsleitung')
    elif org.rechtsform == 'Stiftung' and ib.art == 'geschaeftsfuehrend' and pers.geschlecht == 'M':
        return translate('Geschäftsleitung')
    # AG
    elif org.rechtsform in ('AG', 'Genossenschaft') and ib.art == 'vorstand' and ib.funktion_im_gremium == 'praesident' and pers.geschlecht == 'F':
        return translate('Verwaltungsratspräsidentin')
    elif org.rechtsform in ('AG', 'Genossenschaft') and ib.art == 'vorstand' and ib.funktion_im_gremium == 'praesident' and pers.geschlecht == 'M':
        return translate('Verwaltungsratspräsident')
    elif org.rechtsform in ('AG', 'Genossenschaft') and ib.art == 'vorstand' and ib.funktion_im_gremium == 'vizepraesident' and pers.geschlecht == 'F':
        return translate('Verwaltungsratsvizepräsidentin')
    elif org.rechtsform in ('AG', 'Genossenschaft') and ib.art == 'vorstand' and ib.funktion_im_gremium == 'vizepraesident' and pers.geschlecht == 'M':
        return translate('Verwaltungsratsvizepräsident')
    elif org.rechtsform in ('AG', 'Genossenschaft') and ib.art == 'vorstand' and pers.geschlecht == 'F':
        return translate('Verwaltungsrätin')
    elif org.rechtsform in ('AG', 'Genossenschaft') and ib.art == 'vorstand' and pers.geschlecht == 'M':
        return translate('Verwaltungsrat')
    elif org.rechtsform in ('AG', 'Genossenschaft') and ib.art == 'geschaeftsfuehrend' and ib.funktion_im_gremium == 'praesident' and pers.geschlecht == 'F':
        return translate('Geschäftsführerin (CEO)')
    elif org.rechtsform in ('AG', 'Genossenschaft') and ib.art == 'geschaeftsfuehrend' and ib.funktion_im_gremium == 'praesident' and pers.geschlecht == 'M':
        return translate('Geschäftsführer (CEO)')
    elif org.rechtsform in ('AG', 'Genossenschaft') and ib.art == 'geschaeftsfuehrend' and ib.funktion_im_gremium == 'vizepraesident' and pers.geschlecht == 'F':
        return translate('Vizegeschäftsführerin')
    elif org.rechtsform in ('AG', 'Genossenschaft') and ib.art == 'geschaeftsfuehrend' and ib.funktion_im_gremium == 'vizepraesident' and pers.geschlecht == 'M':
        return translate('Vizegeschäftsführer')
    elif org.rechtsform in ('AG', 'Genossenschaft') and ib.art == 'geschaeftsfuehrend' and pers.geschlecht == 'F':
        return translate('Geschäftsleitung')
    elif org.rechtsform in ('AG', 'Genossenschaft') and ib.art == 'geschaeftsfuehrend' and pers.geschlecht == 'M':
        return translate('Geschäftsleitung')
    # Verein
    elif org.rechtsform == 'Verein' and ib.art == 'vorstand' and ib.funktion_im_gremium == 'praesident' and pers.geschlecht == 'F':
        return translate('Präsidentin')
    elif org.rechtsform == 'Verein' and ib.art == 'vorstand' and ib.funktion_im_gremium == 'praesident' and pers.geschlecht == 'M':
        return translate('Präsident')
    elif org.rechtsform == 'Verein' and ib.art == 'vorstand' and ib.funktion_im_gremium == 'vizepraesident' and pers.geschlecht == 'F':
        return translate('Vizepräsidentin')
    elif org.rechtsform == 'Verein' and ib.art == 'vorstand' and ib.funktion_im_gremium == 'vizepraesident' and pers.geschlecht == 'M':
        return translate('Vizepräsident')
    elif org.rechtsform == 'Verein' and ib.art == 'vorstand' and pers.geschlecht == 'F':
        return translate('Vorstand')
    elif org.rechtsform == 'Verein' and ib.art == 'vorstand' and pers.geschlecht == 'M':
        return translate('Vorstand')
    elif org.rechtsform == 'Verein' and ib.art == 'geschaeftsfuehrend' and ib.funktion_im_gremium == 'praesident' and pers.geschlecht == 'F':
        return translate('Geschäftsführerin')
    elif org.rechtsform == 'Verein' and ib.art == 'geschaeftsfuehrend' and ib.funktion_im_gremium == 'praesident' and pers.geschlecht == 'M':
        return translate('Geschäftsführer')
    elif org.rechtsform == 'Verein' and ib.art == 'geschaeftsfuehrend' and ib.funktion_im_gremium == 'vizepraesident' and pers.geschlecht == 'F':
        return translate('Vizegeschäftsführerin')
    elif org.rechtsform == 'Verein' and ib.art == 'geschaeftsfuehrend' and ib.funktion_im_gremium == 'vizepraesident' and pers.geschlecht == 'M':
        return translate('Vizegeschäftsführer')
    elif org.rechtsform == 'Verein' and ib.art == 'geschaeftsfuehrend' and pers.geschlecht == 'F':
        return translate('Geschäftsleitung')
    elif org.rechtsform == 'Verein' and ib.art == 'geschaeftsfuehrend' and pers.geschlecht == 'M':
        return translate('Geschäftsleitung')
    # Beirat/Patronatskomitee/Expertenkommission/Advisory Board
    elif ib.art == 'beirat':
        return translate('Beirat/Patronatskomitee/Expertenkommission/Advisory Board') + \
               ('' if ib.funktion_im_gremium is None or ib.funktion_im_gremium in ('', 'mitglied') else ', ' + funktion_im_gremium())
    # Else
    else:
        return art() + ('' if ib.funktion_im_gremium is None or ib.funktion_im_gremium in ('', 'mitglied') else ', ' + funktion_im_gremium())
    # TODO add translate() to funktion_im_gremium
    #   return "CONCAT(UCASE(LEFT(interessenbindung.art, 1)), SUBSTRING(interessenbindung.art, 2)),
    #       IF(interessenbindung.funktion_im_gremium IS NULL OR TRIM(interessenbindung.funktion_im_gremium) IN ('', 'mitglied'), '', CONCAT(', ',CONCAT(UCASE(LEFT(interessenbindung.funktion_im_gremium, 1)), SUBSTRING(interessenbindung.funktion_im_gremium, 2))))";


if __name__ == "__main__":
    args = parser.parse_args()

    os.makedirs(f'{str(Path.home())}/.lobbywatch', exist_ok=True)
    try:
        with open(f'{str(Path.home())}/.lobbywatch/twitter-bot-last-message', 'r') as f:
            last_message_time = int(f.readline())
    except FileNotFoundError:
        last_message_time = 0

    if last_message_time + 2*60*60 > time.time():
        print('last message was posted less than one hour ago')
        sys.exit()

    client = tweepy.Client(
        bearer_token=config['TWITTER_ACCESS_TOKEN']
    )

    template_de = "#LobbyNews %parl_name% (%parl_partei%/%parl_kanton%) hat eine neue " \
                  + "Interessenbindung: %interessenbindung_funktion% bei %organisation_name%. Haben Sie das schon deklariert, " \
                  + "%parlamentarier_mention%? %parlamentarier_page%"

    if config.get("SSH_HOST"):
        tunnel = SSHTunnelForwarder(
                (config["SSH_HOST"], int(config["SSH_PORT"])),
                ssh_username=config["SSH_USER"],
                ssh_pkey=paramiko.RSAKey.from_private_key_file(filename=config["SSH_PKEY_FILE"]),
                remote_bind_address=(config["DB_HOST"], int(config["DB_PORT"])))
        tunnel.start()
        host = '127.0.0.1'
        port = tunnel.local_bind_port
    else:
        host = config["DB_HOST"]
        port = int(config["DB_PORT"])

    connection = mysql.connector.connect(
        host=host,
        port=port,
        database=config["DB_DATABASE"],
        user=config['DB_USER'],
        password=config['DB_PASSWORD'],
        use_unicode=True
    )
    cursor = connection.cursor()

    cursor.execute("""
        select q.id, i.*
        from freigabe_queue q
        left join (
            select i.id interessenbindung_id,
                   i.freigabe_datum,
                   i.funktion_im_gremium interessenbindung_funktion,
                   i.art interessenbindung_art,
                   i.beschreibung interessenbindung_beschreibung_de,
                   i.beschreibung_fr interessenbindung_beschreibung_fr,
                   pa.id parlamentarier_id,
                   pa.vorname parlamentarier_vorname,
                   pa.vorname_kurz parlamentarier_vorname_kurz,
                   pa.nachname parlamentarier_nachname,
                   pa.geschlecht parlamentarier_geschlecht,
                   pa.twitter_name parlamentarier_twitter_name,
                   coalesce(p.abkuerzung, '-') parlamentarier_partei_de,
                   coalesce(p.abkuerzung_fr, '-') parlamentarier_partei_fr,
                   k.abkuerzung parlamentarier_kanton,
                   o.name_de organisation_name_de,
                   o.name_fr organisation_name_fr,
                   o.rechtsform organisation_rechtsform,
                   o.twitter_name organisation_twitter_name
            from interessenbindung i 
            join organisation o on i.organisation_id = o.id
            join parlamentarier pa on i.parlamentarier_id = pa.id
            join kanton k on pa.kanton_id = k.id
            left join partei p on pa.partei_id = p.id
            where i.freigabe_datum is not null
              and i.deklarationstyp = 'deklarationspflichtig'
              and i.status != 'deklariert'
              and i.art != 'mitglied'
              and o.rechtsform not in ('Parlamentarische Gruppe', 'Parlamentarische Freundschaftsgruppe')
              and coalesce(i.von, i.created_date) + interval 60 day >= now()
        ) i on q.objekt_id = i.interessenbindung_id and q.objekt_freigabe_datum = i.freigabe_datum
        where q.objekt_typ = 'interessenbindung'
          and q.status = 'neu'
        order by q.objekt_freigabe_datum desc, q.updated_date desc, q.objekt_id desc
        limit 100
    """)

    fields = [md[0] for md in cursor.description]
    for row in [dict(zip(fields, row)) for row in cursor.fetchall()]:
        # print(row['id'])
        status = 'ignoriert' if row['interessenbindung_id'] is None else 'verarbeitet'
        if status == 'verarbeitet':
            pa = Person(geschlecht=row['parlamentarier_geschlecht'])
            ib = Interessenbindung(art=row['interessenbindung_art'], funktion_im_gremium=row['interessenbindung_funktion'])
            org = Organisation(rechtsform=row['organisation_rechtsform'])
            bindungsart = lobbywatch_bindungsart(pa, ib, org, 'de')

            text_de = template_de
            text_de = text_de.replace('%parl_name%', f"{row['parlamentarier_vorname_kurz'] if row['parlamentarier_vorname_kurz'] else row['parlamentarier_vorname']} {row['parlamentarier_nachname']}")
            text_de = text_de.replace('%parl_partei%', row['parlamentarier_partei_de'])
            text_de = text_de.replace('%parl_kanton%', row['parlamentarier_kanton'])
            text_de = text_de.replace('%interessenbindung_funktion%', row['interessenbindung_beschreibung_de'] if row['interessenbindung_beschreibung_de'] else bindungsart)
            text_de = text_de.replace('%organisation_name%', row['organisation_name_de'])
            text_de = text_de.replace('%parlamentarier_mention%', f"@{row['parlamentarier_twitter_name']}" if row['parlamentarier_twitter_name'] else '#' + (row['parlamentarier_vorname']+row['parlamentarier_nachname']).translate(str.maketrans('', '', ' \'-')))
            length = len(unicodedata.normalize('NFC', text_de)) + 2
            text_de = text_de.replace('%parlamentarier_page%', f"https://lobbywatch.ch/de/daten/parlamentarier/{row['parlamentarier_id']}/{urllib.parse.quote(row['parlamentarier_vorname'] + ' ' + row['parlamentarier_nachname'])}")
            if args.dry_run or True:
                print(length, text_de)
            else:
                # if length > 280:
                client = WebClient(token=config['SLACK_BOT_TOKEN'])
                client.chat_postMessage(channel='knut-test', text=text_de)
                # client.create_tweet(text=text_de)
                with open(f'{str(Path.home())}/.lobbywatch/twitter-bot-last-message', 'w') as f:
                    f.write(str(int(time.time())))

        if not args.dry_run:
            cursor.execute("""
                update freigabe_queue
                set    status = %s,
                       updated_date = now()
                where  id = %s
            """, (status, row['id']))

        # only process one message
        if status == 'verarbeitet':
            break

    if not args.dry_run:
        connection.commit()
    tunnel.stop()
