#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path

import mysql.connector
import requests
from dotenv import dotenv_values

from namematch import namematcher

config = {**dotenv_values(".env"), **os.environ}

req_headers = {'Accept': 'application/json'}

colon_re = re.compile('(?!\\B\\[[^]]*):(?![^\\[]*]\\B)')
semicolon_re = re.compile('(?!\\B\\[[^]]*);(?![^\\[]*]\\B)')
ft_type_re = re.compile('<FT TYPE=".">([^<]+)</FT>')
content_key_split_re = re.compile(
    '\. (Beginn|Fusion|Data dello statuto|Date des statuts|Statutendatum|Modification des statuts|Statutenänderung|Statuti modificati|Gründungsstatuten|Statuts|Capital|Capital social|Capitale sociale|Stammkapital|Stammkapital neu|Name neu|Nouveau nom|Nuovo nome|Firma neu|Neue Firma|Nuova ditta|Actions|Aktien|Azioni|Aktien neu|Nouvelles actions|Nuove azioni|Aktienkapital|Capitale azionario|Aktienkapital neu|Nuovo capitale azionario|Vinkulierung|Vinkulierung neu|Nuove traduzioni della ditta|Uebersetzungen der Firma neu|Capitale azionario liberato|Liberierung Aktienkapital|Liberierung Aktienkapital neu|Nuovo capitale azionario liberato|Nouveau siège|Nuova sede|Sitz neu|Domizil neu|But|Scopo|Zweck|Neuer Zweck|Nouveau but|Nouvelle raison de commerce|Nuovo scopo|Zweck neu|Mitteilungen neu|Nouvelles communications|Nuove comunicazioni|Mittel neu|Ausgeschiedene Personen und erloschene Unterschriften|Persone dimissionarie e firme cancellate|Personne radiée|Personne\\(s\\) et signature(s) radiée(s)|Eingetragene Person|Eingetragene Personen|Eingetragene Personen neu oder mutierend|Inscription ou modification de personne(s)|Neu eingetragene Person|Neu eingetragene Personen|Nouvelle gérante|Nouvelle personne inscrite|Nouvelles personnes inscrites|Nuove persone iscritte o modifiche|Persone iscritte|Personne inscrite|Personne inscrite modifiée|Personne(s) inscrite(s)|Personne(s) inscrite(s)|Personnes inscrites|Eingetragene Person geändert|Eingetragene Personen geändert|Nouvelle succursale|Nuova succursale|Zweigniederlassung neu|Altri indirizzi|Autre adresse|Nouvelle autre adresse|Weitere Adresse|Weitere Adressen|Adresse de liquidation|Liquidationsadresse|Sitzverlegung nach|Qualifizierte Tatbestände neu|Urkundenänderung|Neue Sitzbezeichnung|Nouvelle raison sociale|Nuova ragione sociale|Nouvelle forme de droit|Nouvelle nature juridique|Rechtsform neu|Administration|Aufsichtsbehörde neu|Firma Hauptsitz neu|Hauptsitz neu|Gelöschte Person|Gelöschte Personen|Umwandlung|Organisation neu|Nouvel organe de révision|Vermögensübertragung|Neue Identifikationsnummer Hauptsitz|UID neu|Gegenleistung|Organe de publication|Organo di pubblicazione|Publikationsorgan|Nouvel organe de publication|Nuovo organo di pubblicazione|Publikationsorgan neu|Adresse neu|Neue Adresse|Nouvelle adresse|Nuovo recapito|Löschungsgrund|Firma am neuen Sitz|Angaben zur Zweigniederlassung neu|Statutarische Vorrechte neu|Pflichten neu|Partizipationsscheine neu|Uebersetzungen des Namens neu|Partizipationskapital neu|Bemerkungen zum Hauptsitz neu|Liberierung Partizipationskapital neu|Communication aux actionnaires|Communications aux actionnaires|Mitteilung an die Aktionäre|Abspaltung|Statuten neu|Rechtsform Hauptsitz neu|Liquidationsdomizil|Kapital Hauptsitz neu|Vollständige Adresse|Registrierung Hauptsitz neu|Inhaber|Titulaire|Schuldenruf|Postadresse neu|Kommanditsumme neu|Bisherige Firma|Associées-gérantes avec signature individuelle|Gérants avec signature individuelle|Conseil de fondation|Organe de révision|Membres du comité|Personne\\(s\\) inscrite\\(s\\)|Associés|Inscription ou modification de personne\\(s\\)|Comité de direction|Organisation|Membres du comité de direction|Comité|Associé-gérant avec signature individuelle):'.encode(
        'utf-8'), re.IGNORECASE)

parser = argparse.ArgumentParser(description='Process SHAB publications.')
parser.add_argument('--date', dest='ref_date', default=date.today().isoformat(), type=date.fromisoformat)
parser.add_argument('--from', dest='from_date', type=date.fromisoformat)
parser.add_argument('--to', dest='to_date', default=date.today().isoformat(), type=date.fromisoformat)
parser.add_argument('--publ', dest='publ')
parser.add_argument('--json', dest='json_channel')
parser.add_argument('--database', action=argparse.BooleanOptionalAction)


class PersonType(Enum):
    PARLIAMENTARIAN = '🙋️'
    LOBBYIST = '👻'

    def __init__(self, emoji):
        self.emoji = emoji


def unescape_entities(text):
    text = text.replace("&amp;amp;quot", "\"")
    text = text.replace("&amp;amp;", "&")
    text = text.replace("&amp;lt;", "<")
    text = text.replace("&amp;gt;", ">")
    text = text.replace("&amp;apos;", "'")
    text = text.replace("&amp;quot;", "\"")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&apos;", "'")
    text = text.replace("&quot;", "\"")
    return text


def process_publication(publ, format):
    message = unescape_entities(publ['sogcPublication']['message'])
    message = ft_type_re.sub('\\1', message)
    return matcher.match(message, format)


def process_publication_by_key(publ, format):
    message = unescape_entities(publ['sogcPublication']['message'])
    message_bytes = memoryview(ft_type_re.sub('\\1', message).encode('utf-8'))
    ms = []
    matches = content_key_split_re.finditer(message_bytes)
    try:
        match = next(matches)
        key = match.group(1)
        start = match.end()
        for match in matches:
            ms += matcher.match_content(message_bytes[start:match.start()], key, match.start(), format)
            key = match.group(1)
            start = match.end()
        ms += matcher.match_content(message_bytes[start:], key, start, format)
    except StopIteration:
        # print(f"{publ['companyShort']['ehraid']}: {publ['sogcPublication']['sogcId']}")
        pass
    return ms


def create_parliamentarian_matcher(mycursor, ref_date):
    mycursor.execute('''
        select distinct id, vorname, zweiter_vorname, vorname_kurz, nachname, buergerorte
        from parlamentarier pa
        where exists (
            select null
            from in_rat
            where parlamentarier_id = pa.id
            and %(date)s <= coalesce(bis, now())
        )
        order by 1, 3
    ''', {'date': ref_date})
    names = []
    for row in mycursor.fetchall():
        if row[0] == 357:
            n = namematcher.Name((PersonType.PARLIAMENTARIAN, row[0]), 'Nicole Melanie',
                                 tuple(row[2].split(' ')) if row[2] else None, row[3], row[4],
                                 tuple(row[5].split(';')) if row[5] else None)
        else:
            n = namematcher.Name((PersonType.PARLIAMENTARIAN, row[0]), row[1], tuple(row[2].split(' ')) if row[2] else None, row[3],
                                 row[4], tuple(row[5].split(';')) if row[5] else None)
        names.append(n)
    return namematcher.NameMatcher(names=names)


def create_lobbyist_matcher(mycursor, ref_date):
    mycursor.execute('''
        select distinct p.id, vorname, zweiter_vorname, vorname_kurz, nachname, buergerorte
        from person p
                 join zutrittsberechtigung z on p.id = z.person_id
        where %(date)s <= coalesce(z.bis, now())
          and coalesce(buergerorte, '') != 'Unbekannt'
        order by 1, 3
    ''', {'date': ref_date})
    names = []
    for row in mycursor.fetchall():
        if row[0] == 301:
            n = namematcher.Name((PersonType.LOBBYIST, row[0]), '(?:Christian|Karoly)', None, None, 'K[öo]pe',
                                 tuple(row[5].split(';')) if row[5] else None)
        else:
            n = namematcher.Name((PersonType.LOBBYIST, row[0]), row[1], tuple(row[2].split(' ')) if row[2] else None, row[3],
                                 row[4], tuple(row[5].split(';')) if row[5] else None)
        names.append(n)
    return namematcher.NameMatcher(names=names)


def load_publications(ref_date, cache_dir):
    zefix_file = cache_dir.joinpath(f'{ref_date.year}/{ref_date}.json')
    if not zefix_file or not zefix_file.is_file():
        url = f"https://www.zefix.admin.ch/ZefixPublicREST/api/v1/sogc/bydate/{ref_date}"
        resp = requests.get(url, headers=req_headers, auth=(config["ZEFIX_USER"], config["ZEFIX_PASSWORD"]))
        if 200 == resp.status_code:
            if len(resp.content) > 0:
                if zefix_file:
                    zefix_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(zefix_file, 'xb') as f:
                        f.write(resp.content)
    with open(zefix_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def data_loader(args, config):
    if args.publ:
        url = f"https://www.zefix.admin.ch/ZefixPublicREST/api/v1/sogc/{args.publ}"
        resp = requests.get(url, headers=req_headers, auth=(config["ZEFIX_USER"], config["ZEFIX_PASSWORD"]))
        if 200 == resp.status_code:
            yield resp.json()
    elif args.from_date and args.to_date:
        ref_date = args.from_date
        delta = timedelta(days=1)
        while ref_date <= args.to_date:
            for publ in load_publications(ref_date, Path(config['ZEFIX_DIR'])):
                yield publ
            ref_date += delta
    elif args.ref_date:
        for publ in load_publications(args.ref_date, Path(config['ZEFIX_DIR'])):
            yield publ
    else:
        print('error: illegal arguments', args)


class MatchProcessor:
    publ_id = None
    label = ''

    def process(self, publ, match):
        if self.publ_id != publ['sogcPublication']['sogcId']:
            self.publ_id = publ['sogcPublication']['sogcId']
            self.label = ''
            self.process_new_publ(publ, match)
        if self.label != match.label:
            self.label = match.label if match.label else ''
            self.process_new_group(publ, match)
        self.process_publ(publ, match)

    def finalize(self):
        pass

    def process_new_publ(self, publ, match):
        pass

    def process_new_group(self, publ, match):
        pass

    def process_publ(self, publ, match):
        pass


class ConsoleProcessor(MatchProcessor):
    def __init__(self, args):
        self.args = args

    def process_new_publ(self, publ, match):
        uid = publ['companyShort']['uid']
        uid = uid[0:3] + '-' + uid[3:6] + '.' + uid[6:9] + '.' + uid[9:12]
        journal_date = date.fromisoformat(publ['sogcPublication']['registryOfCommerceJournalDate']).strftime('%d.%m.%Y')
        print()
        print(
            f"{publ['companyShort']['name']} ({uid}) - {journal_date} ({self.publ_id}/{publ['sogcPublication']['registryOfCommerceCanton']}):")

    def process_new_group(self, publ, match):
        print(f"\t{str(match.label, 'utf-8') if match.label else '???'}:")

    def process_publ(self, publ, match):
        print('\t\t' + match.format(match.name.id[0].emoji))


class DatabaseProcessor(MatchProcessor):
    def __init__(self, cursor, args):
        self.cursor = cursor
        self.args = args
        self.cursor.execute('''
            insert into shab_match_job(started_at, from_date, to_date)
            values (%(started_at)s, %(from_date)s, %(to_date)s)
        ''', {'started_at': datetime.now(), 'from_date': args.from_date, 'to_date': args.to_date})
        self.job_id = cursor.lastrowid

    def process_publ(self, publ, match):
        uid = publ['companyShort']['uid']
        uid = uid[0:3] + '-' + uid[3:6] + '.' + uid[6:9] + '.' + uid[9:12]
        journal_date = publ['sogcPublication']['registryOfCommerceJournalDate']
        publ_id = publ['sogcPublication']['sogcId']
        zefix_publ_url = f'https://www.zefix.ch/en/search/entity/list/firm/{ehraid}#shabPub-{publ_id}'
        self.cursor.execute('''
            insert into shab_name_match(job_id, company_name, uid, publ_id, publ_url, canton, journal_date, publ_date, parlamentarier_id, person_id, label, offset, extract)
            values (%(job_id)s, %(company_name)s, %(uid)s, %(publ_id)s, %(publ_url)s, %(canton)s, %(journal_date)s, %(publ_date)s, %(parlamentarier_id)s, %(person_id)s, %(label)s, %(offset)s, %(extract)s)
        ''', {'job_id': self.job_id, 'company_name': publ['companyShort']['name'], 'uid': uid,
              'publ_id': publ_id, 'publ_url': zefix_publ_url,
              'canton': publ['sogcPublication']['registryOfCommerceCanton'],
              'journal_date': journal_date,
              'publ_date': publ['sogcPublication']['sogcDate'], 'parlamentarier_id': match.name.id[1] if match.name.id[0] == PersonType.PARLIAMENTARIAN else None,
              'person_id': match.name.id[1] if match.name.id[0] == PersonType.LOBBYIST else None, 'label': str(match.label, 'utf-8'), 'offset': match.message_offset,
              'extract': match.format(match.name.id[0].emoji)})

    def finalize(self):
        self.cursor.execute('''
            update shab_match_job
            set finished_at = %(finished_at)s
            where id = %(id)s
        ''', {'id': self.job_id, 'finished_at': datetime.now()})


class SlackProcessor(MatchProcessor):
    text_blocks = []
    current_block = None

    def __init__(self, args):
        self.args = args

    def process_new_publ(self, publ, match):
        company_name = publ['companyShort']['name']
        publ_id = publ['sogcPublication']['sogcId']
        ehraid = publ['companyShort']['ehraid']
        uid = publ['companyShort']['uid']
        uid = uid[0:3] + '-' + uid[3:6] + '.' + uid[6:9] + '.' + uid[9:12]
        reg_company_url = registries[registry].replace("#", uid)
        canton = publ['sogcPublication']['registryOfCommerceCanton']
        journal_date = date.fromisoformat(publ['sogcPublication']['registryOfCommerceJournalDate']).strftime('%d.%m.%Y')
        zefix_publ_url = f'https://www.zefix.ch/en/search/entity/list/firm/{ehraid}#shabPub-{publ_id}'
        self.current_block = {'type': 'section',
                              'text': {
                                  'type': 'mrkdwn',
                                  'text': f'<{reg_company_url}|{company_name}> - {journal_date} <{zefix_publ_url}|{publ_id}>/{canton}'
                              },
                              'accessory': {
                                  'type': 'checkboxes',
                                  'options': [],
                                  'action_id': f'publication_matches-{publ_id}'
                              }}
        self.text_blocks.append(self.current_block)

    def process_publ(self, publ, match):
        desc = match.format(match.name.id[0].emoji)
        self.current_block['accessory']['options'].append({
            'text': {
                'type': 'plain_text',
                'text': str(match.label, 'utf-8') if match.label else '???'
            },
            'description': {
                'type': 'mrkdwn',
                'text': desc[:147] + (desc[147:] and '...')
            },
            'value': 'match_at_offset-' + str(match.message_offset)
        })

    def finalize(self):
        if self.args.json_channel == 'slack':
            # TODO add leading section about date and number of publications
            resp = requests.post(config['SLACK_WEBHOOK_URL'], json={'blocks': self.text_blocks})
            if resp.status_code != 200:
                print(resp.text, json.dumps(self.text_blocks, indent=2))
        elif self.args.json_channel == 'slack-test':
            # TODO add leading section about date and number of publications
            resp = requests.post(config['SLACK_TEST_WEBHOOK_URL'], json={'blocks': self.text_blocks})
            if resp.status_code != 200:
                print(resp.text, json.dumps(self.text_blocks, indent=2))
        elif self.args.json_channel == 'console':
            print(json.dumps(self.text_blocks, indent=2))


if __name__ == "__main__":
    args = parser.parse_args()
    if args.from_date and args.from_date > args.to_date:
        print('error: from_date must be before to_date')
        sys.exit(1)
    elif args.from_date and (args.from_date > date.today() or args.to_date > date.today()):
        print('error: from_date and to_date must not be in the future')
        sys.exit(1)

    connection = mysql.connector.connect(
        host=config["DB_HOST"],
        database="lobbywatch_public",
        user=config['DB_USER'],
        password=config['DB_PASSWORD'],
        use_unicode=True
    )
    connection.autocommit = True
    cursor = connection.cursor()

    data = data_loader(args, config)
    if not data:
        print('no data to process')
        sys.exit(0)
    elif args.publ:
        data = list(data)

    ref_date = args.from_date if args.from_date else data[0]['sogcPublication']['registryOfCommerceJournalDate'] if args.publ else args.ref_date
    ref_date = date.fromisoformat('2018-06-01')
    parliamentarians = create_parliamentarian_matcher(cursor, ref_date)
    lobbyists = create_lobbyist_matcher(cursor, ref_date)

    url = 'https://www.zefix.admin.ch/ZefixPublicREST/api/v1/registryOfCommerce'
    resp = requests.get(url, headers=req_headers, auth=(config["ZEFIX_USER"], config["ZEFIX_PASSWORD"]))
    registries = {}
    if resp.status_code == 200:
        for reg in resp.json():
            registries[reg['registryOfCommerceId']] = reg['url2']
    else:
        print('error', resp.status_code, resp.content)

    if args.publ:
        print(f'Processing publications {args.publ} ...')
    elif args.from_date:
        print(f'Processing publications {args.from_date} .. {args.to_date} ...')
    else:
        print(f'Processing publications {args.ref_date} ...')

    processors = []
    if args.json_channel:
        processors.append(SlackProcessor(args))
    if args.database:
        processors.append(DatabaseProcessor(cursor, args))
    if not args.json_channel or args.json_channel != 'console':
        processors.append(ConsoleProcessor(args))

    for publ in data:
        ehraid = publ['companyShort']['ehraid']
        uid = publ['companyShort']['uid']
        uid = uid[0:3] + '-' + uid[3:6] + '.' + uid[6:9] + '.' + uid[9:12]
        publ_id = publ['sogcPublication']['sogcId']
        canton = publ['sogcPublication']['registryOfCommerceCanton']
        registry = publ['sogcPublication']['registryOfCommerceId']

        regCompanyUrl = registries[registry].replace("#", uid)
        zefixPublUrl = f'https://www.zefix.ch/en/search/entity/list/firm/{ehraid}#shabPub-{publ_id}'

        formats = ['vd'] if canton in ('VD', 'GE', 'NE') else ['fr', 'vd'] if canton == 'FR' else ['std']

        found = False
        for format in formats:
            if found:
                break
            for matcher in [parliamentarians, lobbyists]:
                matches = process_publication_by_key(publ, format)
                for m in matches:
                    for proc in processors:
                        proc.process(publ, m)
                    found = True

    for proc in processors:
        proc.finalize()
    connection.commit()
