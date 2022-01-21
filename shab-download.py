#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re
from datetime import date
from pathlib import Path

import mysql.connector
import requests
from dotenv import dotenv_values

from namematch import namematcher

config = {**dotenv_values(".env"), **os.environ}

req_headers = {'Accept': 'application/json'}

colon_re = re.compile('(?!\\B\\[[^]]*):(?![^\\[]*]\\B)')
semicolon_re = re.compile('(?!\\B\\[[^]]*);(?![^\\[]*]\\B)')

parser = argparse.ArgumentParser(description='Process SHAB publications.')
parser.add_argument('--date', dest='ref_date', default=date.today().isoformat(), type=date.fromisoformat)
parser.add_argument('--publ', dest='publ')
parser.add_argument('--json', dest='json_channel')


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
    message = re.sub('<FT TYPE=".">([^<]+)</FT>', '\\1', message)
    return matcher.match(message, format)


if __name__ == "__main__":
    args = parser.parse_args()
    ref_date = args.ref_date
    publ_id = args.publ
    json_channel = args.json_channel

    mydb = mysql.connector.connect(
        host=config["DB_HOST"],
        database="lobbywatch_public",
        user=config['DB_USER'],
        password=config['DB_PASSWORD']
    )
    mycursor = mydb.cursor()

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
        n = namematcher.Name(row[0], row[1], row[2].split(' ') if row[2] else None, row[3], row[4],
                             row[5].split(';') if row[5] else None)
        if n.id == 357:
            n.first = 'Nicole Melanie'
        names.append(n)
    parliamentarians = namematcher.NameMatcher(names=names)

    mycursor.execute('''
        select distinct p.id, vorname, zweiter_vorname, vorname_kurz, nachname, buergerorte
        from person p
                 join zutrittsberechtigung z on p.id = z.person_id
        where %(date)s <= coalesce(z.bis, now())
          and buergerorte != 'Unbekannt'
        order by 1, 3
    ''', {'date': ref_date})
    names = []
    for row in mycursor.fetchall():
        n = namematcher.Name(row[0], row[1], row[2].split(' ') if row[2] else None, row[3], row[4],
                             row[5].split(';') if row[5] else None)
        if n.id == 301:
            n.nick = None
            n.middle = None
            n.first = '(?:Christian|Karoly)'
            n.last = 'K[öo]pe'
        names.append(n)
    lobbyists = namematcher.NameMatcher(names=names)

    url = 'https://www.zefix.admin.ch/ZefixPublicREST/api/v1/registryOfCommerce'
    resp = requests.get(url, headers=req_headers, auth=(config["ZEFIX_USER"], config["ZEFIX_PASSWORD"]))
    registries = {}
    if resp.status_code == 200:
        for reg in resp.json():
            registries[reg['registryOfCommerceId']] = reg['url2']
    else:
        print('error', resp.status_code, resp.content)

    zefix_file = Path(config['ZEFIX_DIR']).joinpath(f'{ref_date.year}/{ref_date}.json') if config.get('ZEFIX_DIR') else None

    data = None
    if publ_id:
        url = f"https://www.zefix.admin.ch/ZefixPublicREST/api/v1/sogc/{publ_id}"
        resp = requests.get(url, headers=req_headers, auth=(config["ZEFIX_USER"], config["ZEFIX_PASSWORD"]))
        if 200 == resp.status_code:
            data = [resp.json()]
    elif zefix_file and zefix_file.is_file():
        with open(zefix_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        url = f"https://www.zefix.admin.ch/ZefixPublicREST/api/v1/sogc/bydate/{ref_date}"
        resp = requests.get(url, headers=req_headers, auth=(config["ZEFIX_USER"], config["ZEFIX_PASSWORD"]))
        if 200 == resp.status_code:
            data = resp.json()
            if len(resp.content) > 0:
                if zefix_file:
                    print(f'saving to {zefix_file}')
                    zefix_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(zefix_file, 'xb') as f:
                        f.write(resp.content)
        else:
            print('error', resp.status_code, resp.content)

    if data:
        print(f'Processing {len(data)} publications {publ_id if publ_id else f"for {ref_date}"} ...')

        text_blocks = []
        current_block = None

        for publ in data:
            companyName = publ['companyShort']['name']
            uid = publ['companyShort']['uid']
            ehraid = publ['companyShort']['ehraid']
            uid = uid[0:3] + '-' + uid[3:6] + '.' + uid[6:9] + '.' + uid[9:12]
            publId = publ['sogcPublication']['sogcId']
            canton = publ['sogcPublication']['registryOfCommerceCanton']
            registry = publ['sogcPublication']['registryOfCommerceId']
            journalDate = date.fromisoformat(publ['sogcPublication']['registryOfCommerceJournalDate']).strftime('%d.%m.%Y')

            regCompanyUrl = registries[registry].replace("#", uid)
            zefixPublUrl = f'https://www.zefix.ch/en/search/entity/list/firm/{ehraid}#shabPub-{publId}'

            formats = ['vd'] if canton in ('VD', 'GE', 'NE') else ['fr', 'vd'] if canton == 'FR' else ['std']

            found = False
            for format in formats:
                if found:
                    break
                for matcher in [parliamentarians, lobbyists]:
                    emoji = '🙋️' if matcher == parliamentarians else '👻'
                    first = True
                    label = None
                    for m in process_publication(publ, format):
                        found = True
                        desc = m.format(emoji)
                        if first:
                            first = False
                            print()
                            print(f'{companyName} ({uid}) - {journalDate} ({publId}/{canton}):')
                            current_block = {'type': 'section',
                                             'text': {
                                                 'type': 'mrkdwn',
                                                 'text': f'<{regCompanyUrl}|{companyName}> - {journalDate} <{zefixPublUrl}|{publId}>/{canton}'
                                             },
                                             'accessory': {
                                                 'type': 'checkboxes',
                                                 'options': [],
                                                 'action_id': f'publication_matches-{publId}'
                                             }}
                            text_blocks.append(current_block)

                        if m.label:
                            print('\t' + m.label + ':')
                            print('\t\t' + desc)
                        else:
                            print('\t' + desc)

                        current_block['accessory']['options'].append({
                            'text': {
                                'type': 'plain_text',
                                'text': m.label if m.label else '???'
                            },
                            'description': {
                                'type': 'mrkdwn',
                                'text': desc[:147] + (desc[147:] and '...')
                            },
                            'value': 'match_at_offset-' + str(m.message_offset)
                        })

        if text_blocks and json_channel:
            if json_channel == 'slack':
                # TODO add leading section about date and number of publications
                resp = requests.post(config['SLACK_WEBHOOK_URL'], json={'blocks': text_blocks})
                if resp.status_code != 200:
                    print(resp.text, json.dumps(text_blocks, indent=2))
            elif json_channel == 'slack-test':
                # TODO add leading section about date and number of publications
                resp = requests.post(config['SLACK_TEST_WEBHOOK_URL'], json={'blocks': text_blocks})
                if resp.status_code != 200:
                    print(resp.text, json.dumps(text_blocks, indent=2))
            elif json_channel == 'console':
                print(json.dumps(text_blocks, indent=2))
