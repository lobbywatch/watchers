#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import urllib.parse
from collections import namedtuple

import mysql.connector
import paramiko
import regex as re
import requests
import unicodedata
from dotenv import dotenv_values
from slack_bolt import App
from sshtunnel import SSHTunnelForwarder

config = {**dotenv_values(".env"), **os.environ}

parser = argparse.ArgumentParser(description='Erstellt für neu freigegebene Interessenbindungen Slack Messages womit Twitter Posts ausgelöst werden können.')
parser.add_argument('--dry-run', action=argparse.BooleanOptionalAction)

URL_PATTERN = r'[A-Za-z0-9]+://[A-Za-z0-9%-_]+(/[A-Za-z0-9%-_])*(#|\\?)[A-Za-z0-9%-_&=]*'

Person = namedtuple('Person', 'geschlecht')
Interessenbindung = namedtuple('Interessenbindung', 'art funktion_im_gremium')
Organisation = namedtuple('Organisation', 'rechtsform')

app = App(token=config["SLACK_BOT_TOKEN"])


def lobbywatch_bindungsart(pers, ib, org, lang):
    def translate(key):
        cursor.execute('''
            select case when t.translation = '' then s.source else t.translation end
            from translation_source s
            join translation_target t on t.translation_source_id = s.id
            where binary source = %(key)s
              and t.lang = %(lang)s
              and s.location = '_lobbywatch_bindungsart()'
              and s.context = ''
        ''', {'key': key, 'lang': lang})
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


def tweet_text(template, lang, row):
    text = template
    text = text.replace('%parl_name%',
                        f"{row['parlamentarier_vorname_kurz'] if row['parlamentarier_vorname_kurz'] else row['parlamentarier_vorname']} {row['parlamentarier_nachname']}")
    text = text.replace('%parl_pronomen_fr%', f"{'elle' if row['parlamentarier_geschlecht'] == 'F' else 'il'}")
    text = text.replace('%parl_partei%', row[f'parlamentarier_partei_{lang}'])
    text = text.replace('%parl_kanton%', row['parlamentarier_kanton'])
    text = text.replace('%interessenbindung_funktion%',
                        row[f'interessenbindung_beschreibung_{lang}'] if row[
                            f'interessenbindung_beschreibung_{lang}'] else lobbywatch_bindungsart(pa, ib, org, lang))
    text = text.replace('%organisation_name%', row[f'organisation_name_{lang}'] if row[f'organisation_name_{lang}'] else row['organisation_name_de'])
    text = text.replace('%parlamentarier_mention%',
                              f"@{row['parlamentarier_twitter_name']}" if row['parlamentarier_twitter_name'] else '#' + (
                                          row['parlamentarier_vorname'] + row['parlamentarier_nachname']).translate(
                                  str.maketrans('', '', ' \'-')))
    text = text.replace('%parlamentarier_page%',
                              f"https://lobbywatch.ch/{lang}/daten/parlamentarier/{row['parlamentarier_id']}/{urllib.parse.quote(row['parlamentarier_vorname'] + ' ' + row['parlamentarier_nachname'])}")
    return text


def post_slack_message(pa, ib, org, row):
    text_de = tweet_text(templates['de'], 'de', row)
    length_de = len(unicodedata.normalize('NFC', re.sub(URL_PATTERN, '12345678901234567890123', text_de)))
    text_fr = tweet_text(templates['fr'], 'fr', row)
    length_fr = len(unicodedata.normalize('NFC', re.sub(URL_PATTERN, '12345678901234567890123', text_fr)))

    if args.dry_run:
        print(length_de, text_de)
        print(length_fr, text_fr)
    else:
        # if length > 280:
        text_blocks = [
            {
                "type": "section",
                "block_id": "tweet_block",
                "text": {
                    "text": f"Interessenbindung <https://cms.lobbywatch.ch/bearbeitung/interessenbindung.php?operation=view&pk0={row['interessenbindung_id']}|{row['parlamentarier_vorname_kurz'] if row['parlamentarier_vorname_kurz'] else row['parlamentarier_vorname']} {row['parlamentarier_nachname']} - {row['organisation_name_de']}>",
                    "type": "mrkdwn"
                },
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Deutsch ({length_de}/280)*"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Französisch ({length_fr}/280)*"
                    },
                    {
                        "type": "plain_text",
                        "text": text_de
                    },
                    {
                        "type": "plain_text",
                        "text": text_fr
                    }
                ]
            },
            {
                "type": "actions",
                "block_id": f"{row['id']}",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Posten"
                        },
                        "style": "primary",
                        "value": "click_me_456",
                        "action_id": "tweet_post"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Bearbeiten DE"
                        },
                        "value": "click_me_456",
                        "action_id": "tweet_edit_de"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Bearbeiten FR"
                        },
                        "value": "click_me_456",
                        "action_id": "tweet_edit_fr"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Verwerfen"
                        },
                        "style": "danger",
                        "value": "click_me_456",
                        "action_id": "tweet_cancel"
                    },
                ]
            },
        ]
        app.client.chat_postMessage(channel='social-media-bot', blocks=text_blocks)


def db_connection():
    if "SSH_HOST" in config:
        tunnel = SSHTunnelForwarder(
            (config["SSH_HOST"], int(config["SSH_PORT"])),
            ssh_username=config["SSH_USER"],
            ssh_pkey=paramiko.RSAKey.from_private_key_file(filename=config["SSH_PKEY_FILE"]),
            remote_bind_address=(config["DB_HOST"], int(config["DB_PORT"])))
        tunnel.start()
        host = '127.0.0.1'
        port = tunnel.local_bind_port
    else:
        tunnel = None
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
    return tunnel, connection


if __name__ == "__main__":
    args = parser.parse_args()

    # os.makedirs(f'{str(Path.home())}/.lobbywatch', exist_ok=True)
    # try:
    #     with open(f'{str(Path.home())}/.lobbywatch/twitter-bot-last-message', 'r') as f:
    #         last_message_time = int(f.readline())
    # except FileNotFoundError:
    #     last_message_time = 0
    #
    # if last_message_time + 2*60*60 > time.time():
    #     print('last message was posted less than one hour ago')
    #     sys.exit()

    templates = {'de': "#LobbyNews %parl_name% (%parl_partei%/%parl_kanton%) hat eine neue Interessenbindung: " \
                  + "%interessenbindung_funktion% bei %organisation_name%. Haben Sie das schon deklariert, " \
                  + "%parlamentarier_mention%? %parlamentarier_page%",
                 'fr': "#LobbyNews %parl_name% (%parl_partei%/%parl_kanton%) a un nouveau lien d'intérêt : " \
                  "%parl_pronomen_fr% est %interessenbindung_funktion% de %organisation_name%. L'avez-vous déjà signalé aux Services du Parlement " \
                  "%parlamentarier_mention%? %parlamentarier_page%"}

    tunnel, connection = db_connection()
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
              and least(coalesce(i.von, i.created_date), i.created_date) + interval 60 day >= now()
        ) i on q.objekt_id = i.interessenbindung_id and q.objekt_freigabe_datum = i.freigabe_datum
        where q.objekt_typ = 'interessenbindung'
          and q.status = 'neu'
        order by q.objekt_freigabe_datum desc, q.updated_date desc, q.objekt_id desc
        # limit 100
    """)

    fields = [md[0] for md in cursor.description]
    for row in [dict(zip(fields, row)) for row in cursor.fetchall()]:
        status = None
        if row['interessenbindung_id'] is None:
            status = 'ignoriert'
        else:
            response = requests.get(f'https://cms.lobbywatch.ch/de/data/interface/v1/json/table/interessenbindung/flat/id/{row["interessenbindung_id"]}')
            if response.status_code == 200:
                status = 'in_triage'

        if status == 'in_triage':
            pa = Person(geschlecht=row['parlamentarier_geschlecht'])
            ib = Interessenbindung(art=row['interessenbindung_art'], funktion_im_gremium=row['interessenbindung_funktion'])
            org = Organisation(rechtsform=row['organisation_rechtsform'])

            post_slack_message(pa, ib, org, row)

        if status and not args.dry_run:
            cursor.execute("""
                update freigabe_queue
                set    status = %s,
                       updated_date = now()
                where  id = %s
            """, (status, row['id']))

        # # only process one message
        # if status == 'in_triage':
        #     break

    if not args.dry_run:
        connection.commit()
    if tunnel:
        tunnel.stop()
