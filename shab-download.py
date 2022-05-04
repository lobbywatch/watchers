#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import ndjson
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import mysql.connector
import regex as re
import requests
from dotenv import dotenv_values

from namematch.lobbywatch import PersonType, NameSet, create_matchers_from_database
from namematch.namematcher import MatchFormat, NameMatcher, Name

config = {**dotenv_values(".env"), **os.environ}

req_headers = {'Accept': 'application/json'}

registries = {}

colon_re = re.compile('(?!\\B\\[[^]]*):(?![^\\[]*]\\B)')
semicolon_re = re.compile('(?!\\B\\[[^]]*);(?![^\\[]*]\\B)')
ft_type_re = re.compile('<FT TYPE=".">([^<]+)</FT>')
content_key_split_re = re.compile('\\. ([^:0-9,.;[\]]+):'.encode('utf-8'))

parser = argparse.ArgumentParser(description='Process SHAB publications.')
parser.add_argument('--date', dest='ref_date', default=date.today().isoformat(), type=date.fromisoformat)
parser.add_argument('--from', dest='from_date', type=date.fromisoformat)
parser.add_argument('--to', dest='to_date', default=date.today().isoformat(), type=date.fromisoformat)
parser.add_argument('--publ', dest='publ')
parser.add_argument('--json', dest='json_channel')
parser.add_argument('--names', dest='names', choices=['current', 'research'], default='current')
parser.add_argument('--names-file', dest='names_file', type=argparse.FileType('r'))
parser.add_argument('--database', action=argparse.BooleanOptionalAction)


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


def process_publication_by_key(publ, matcher, format):
    message = unescape_entities(publ['sogcPublication']['message'])
    message_bytes = memoryview(ft_type_re.sub('\\1', message).encode('utf-8'))
    ms = []
    matches = content_key_split_re.finditer(message_bytes)
    start = 0
    key = b'Unzugeordnet'
    try:
        match = next(matches)
        key = match.group(1)
        start = match.end()
        ms += matcher.match_content(message_bytes[0:start], b'Unzugeordnet', 0, format)
        for match in matches:
            ms += matcher.match_content(message_bytes[start:match.start()], key, match.start(), format)
            key = match.group(1)
            start = match.end()
        ms += matcher.match_content(message_bytes[start:], key, start, format)
    except StopIteration:
        ms += matcher.match_content(message_bytes[start:], key, 0, format)
    return ms


def load_publications(ref_date, cache_dir):
    zefix_file = cache_dir.joinpath(f'{ref_date.year}/{ref_date}.ndjson')
    if not zefix_file or not zefix_file.is_file():
        url = f"https://www.zefix.admin.ch/ZefixPublicREST/api/v1/sogc/bydate/{ref_date}"
        resp = requests.get(url, headers=req_headers, auth=(config["ZEFIX_USER"], config["ZEFIX_PASSWORD"]))
        if 200 == resp.status_code:
            if len(resp.content) > 0:
                if zefix_file:
                    zefix_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(zefix_file, 'x') as f:
                        ndjson.dump(json.loads(resp.content), f)
    with open(zefix_file, 'r', encoding='utf-8') as f:
        return ndjson.load(f)


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
        print('\t\t' + match.format(match.name.id[0].emoji if type(match.name.id) is tuple else ''))


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
        ehraid = publ['companyShort']['ehraid']
        uid = publ['companyShort']['uid']
        uid = uid[0:3] + '-' + uid[3:6] + '.' + uid[6:9] + '.' + uid[9:12]
        journal_date = publ['sogcPublication']['registryOfCommerceJournalDate']
        publ_id = publ['sogcPublication']['sogcId']
        reg_company_url = get_registry_company_url(publ)
        zefix_publ_url = f'https://www.zefix.ch/en/search/entity/list/firm/{ehraid}#shabPub-{publ_id}'
        self.cursor.execute('''
            insert into shab_name_match(job_id, company_name, uid, reg_company_url, publ_id, publ_url, canton, journal_date, publ_date, parlamentarier_id, person_id, other_id, label, offset, extract, mutations)
            values (%(job_id)s, %(company_name)s, %(uid)s, %(reg_company_url)s, %(publ_id)s, %(publ_url)s, %(canton)s, %(journal_date)s, %(publ_date)s, %(parlamentarier_id)s, %(person_id)s, %(other_id)s, %(label)s, %(offset)s, %(extract)s, %(mutations)s)
        ''', {'job_id': self.job_id, 'company_name': publ['companyShort']['name'], 'uid': uid,
              'reg_company_url': reg_company_url,
              'publ_id': publ_id, 'publ_url': zefix_publ_url,
              'canton': publ['sogcPublication']['registryOfCommerceCanton'],
              'journal_date': journal_date,
              'publ_date': publ['sogcPublication']['sogcDate'],
              'parlamentarier_id': match.name.id[1] if match.name.id[0] == PersonType.PARLIAMENTARIAN else None,
              'person_id': match.name.id[1] if match.name.id[0] == PersonType.LOBBYIST else None,
              'other_id': match.name.id[1] if match.name.id[0] == PersonType.OTHER else None,
              'label': str(match.label, 'utf-8'), 'offset': match.message_offset,
              'extract': match.format(match.name.id[0].emoji),
              'mutations': json.dumps([d['key'] for d in publ['sogcPublication']['mutationTypes']])})

    def finalize(self):
        self.cursor.execute('''
            update shab_match_job
            set finished_at = now()
            where id = %(id)s
        ''', {'id': self.job_id})


class SlackProcessor(MatchProcessor):
    text_blocks = []
    current_block = None

    def __init__(self, args):
        self.args = args

    def process_new_publ(self, publ, match):
        company_name = publ['companyShort']['name']
        publ_id = publ['sogcPublication']['sogcId']
        ehraid = publ['companyShort']['ehraid']
        reg_company_url = get_registry_company_url(publ)
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


def get_registry_company_url(publ):
    uid = publ['companyShort']['uid']
    registry = publ['sogcPublication']['registryOfCommerceId']
    return registries[registry].replace("#", uid[0:3] + '-' + uid[3:6] + '.' + uid[6:9] + '.' + uid[9:12])


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

    ref_date = args.from_date if args.from_date else data[0]['sogcPublication'][
        'registryOfCommerceJournalDate'] if args.publ else args.ref_date
    if args.names_file:
        with args.names_file as json_file:
            names = [json.loads(jline, object_hook=lambda o: Name(id=(PersonType.OTHER, o['id']), first=o['first'],
                                                                  middle=tuple(o['middle']) if o.get('middle') else None,
                                                                  last=o['last'], nick=o.get('nick'),
                                                                  citizenships=o.get('citizenships'))) for jline in json_file]
        matchers = [NameMatcher(names=names)]
    else:
        matchers = create_matchers_from_database(cursor, ref_date, NameSet.CURRENT if args.names == 'current' else NameSet.RESEARCH)

    url = 'https://www.zefix.admin.ch/ZefixPublicREST/api/v1/registryOfCommerce'
    resp = requests.get(url, headers=req_headers, auth=(config["ZEFIX_USER"], config["ZEFIX_PASSWORD"]))
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
        publ_id = publ['sogcPublication']['sogcId']
        if not publ['companyShort']['uid']:
            print(f'error: skipping publication {publ_id} without uid')
            continue

        canton = publ['sogcPublication']['registryOfCommerceCanton']
        formats = [MatchFormat.SHAB_VD] if canton in ('VD', 'GE', 'NE') \
            else [MatchFormat.SHAB_FR, MatchFormat.SHAB_VD] if canton == 'FR' \
            else [MatchFormat.SHAB_STD]

        found = False
        for format in formats:
            if found:
                break
            for matcher in matchers:
                matches = process_publication_by_key(publ, matcher, format)
                for m in matches:
                    for proc in processors:
                        proc.process(publ, m)
                    found = True

    for proc in processors:
        proc.finalize()
    connection.commit()
