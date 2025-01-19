#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

import mysql.connector
import requests

from dotenv import dotenv_values
config = dotenv_values(".env")

req_headers = {
    'Accept': 'application/json'
}

if __name__ == "__main__":
    mydb = mysql.connector.connect(
        host=config["DB_HOST"],
        database="lobbywatch_public",
        user=config['DB_USER'],
        password=config['DB_PASSWORD']
    )

    mycursor = mydb.cursor()
    mycursor.execute("select id, parlament_biografie_id from parlamentarier")
    for row in mycursor.fetchall():
        url = f"https://ws.parlament.ch/OData.svc/Person(ID={row[1]},Language='DE')/Citizenships?$format=json&$orderby=PostCode"
        resp = requests.get(url, headers=req_headers)
        if resp.status_code == 200:
            data = json.loads(resp.content.decode('utf-8'))
            buergerorte = [e['City'] for e in data['d']]
            mycursor.execute("update parlamentarier set buergerorte = %s where id = %s", (';'.join(buergerorte), row[0]))

    mydb.commit()
