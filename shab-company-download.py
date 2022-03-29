#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import time
from pathlib import Path
from textwrap import dedent

import mysql.connector
import requests
import xmltodict
from dotenv import dotenv_values

config = {**dotenv_values(".env"), **os.environ}

req_headers = {'Accept': 'application/json'}

registries = {}


def load_company(uid, cache_dir):
    uid_file = cache_dir.joinpath(f'company-uid/{uid}.json')
    if not uid_file or not uid_file.is_file():
        body = dedent(f"""
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:uid="http://www.uid.admin.ch/xmlns/uid-wse" xmlns:ns="http://www.ech.ch/xmlns/eCH-0097/5">
             <soapenv:Header/>
             <soapenv:Body>
                <uid:GetByUID>
                   <uid:uid>
                      <ns:uidOrganisationIdCategorie>CHE</ns:uidOrganisationIdCategorie>
                      <ns:uidOrganisationId>{uid.replace('-', '').replace('.', '')[3:]}</ns:uidOrganisationId>
                   </uid:uid>
                </uid:GetByUID>
             </soapenv:Body>
            </soapenv:Envelope>
        """)
        url = 'https://www.uid-wse.admin.ch/V5.0/PublicServices.svc?wsdl'
        resp = requests.post(url, data=body.encode('utf-8'),
                             headers={'Content-Type': 'text/xml; charset=utf-8',
                                      'SoapAction': 'http://www.uid.admin.ch/xmlns/uid-wse/IPublicServices/GetByUID'})
        if 200 == resp.status_code:
            uid_file.parent.mkdir(parents=True, exist_ok=True)
            with open(uid_file, 'wb') as f:
                f.write(json.dumps(
                    remove_xml_artifacts(
                        xmltodict.parse(resp.content)['s:Envelope']['s:Body']['GetByUIDResponse']['GetByUIDResult'][
                            'organisationType']['organisation']), indent=2).encode('utf-8'))
            time.sleep(3)
        else:
            print(resp.status_code, resp.text)
            if resp.text.find('Request_limit_exceeded') > 0:
                time.sleep(60)


def remove_xml_artifacts(d):
    if d.get('@xmlns'):
        del d['@xmlns']
    for k, v in d.items():
        if isinstance(v, dict):
            d[k] = remove_xml_artifacts(v)
            if v.keys() == {'#text'}:
                d[k] = v['#text']
        elif isinstance(v, list):
            d[k] = [remove_xml_artifacts(x) for x in v]
    return d

if __name__ == "__main__":
    connection = mysql.connector.connect(
        host=config["DB_HOST"],
        database="lobbywatch_public",
        user=config['DB_USER'],
        password=config['DB_PASSWORD'],
        use_unicode=True
    )
    cursor = connection.cursor()

    cursor.execute('select uid from organisation where coalesce(land_id, 191) = 191 and uid is not null')
    for row in cursor.fetchall():
        print(f'Fetching {row[0]} ...')
        load_company(row[0], Path(config["ZEFIX_DIR"]))
