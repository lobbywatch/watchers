#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import regex as re
import sys
from namematch.namematcher import MatchFormat, NameMatcher, Name
from namematch.lobbywatch import PersonType

parl_names = []
with open('parliamentarians.ndjson', 'r', encoding='utf-8') as f:
    for line in f:
        parl_names.append(json.loads(line, object_hook=lambda d: Name(id=(PersonType.PARLIAMENTARIAN, d['id']), first=d['first'],
                                                                      middle=tuple(d['middle'].split(' ')) if d['middle'] else None, nick=d['nick'], last=d['last'],
                                                                      citizenships=None)))

lobby_names = []
with open('lobbyists.ndjson', 'r', encoding='utf-8') as f:
    for line in f:
        lobby_names.append(json.loads(line, object_hook=lambda d: Name(id=(PersonType.LOBBYIST, d['id']), first=d['first'],
                                                                      middle=tuple(d['middle'].split(' ')) if d['middle'] else None, nick=d['nick'], last=d['last'],
                                                                      citizenships=None)))

parl_matcher = NameMatcher(parl_names, formats=[MatchFormat.NAME_ONLY])
lobby_matcher = NameMatcher(lobby_names, formats=[MatchFormat.NAME_ONLY])

#       ‌ ‎ ‏ ​ ­
stdin = sys.stdin.read().replace('\xc2\xa0', ' ').replace(' ', ' ')
matches = parl_matcher.match_content(stdin.encode(encoding='utf-8'), label=None, offset=0, format=MatchFormat.NAME_ONLY)
matches += lobby_matcher.match_content(stdin.encode(encoding='utf-8'), label=None, offset=0, format=MatchFormat.NAME_ONLY)
matches.sort(key=lambda m: m.start)
for m in matches:
    emoji = m.name.id[0].emoji if type(m.name.id) is tuple else ''
    print(re.sub('\\s+', ' ', f'{emoji}{str(m.message[m.start:m.end], "utf-8")}{emoji}'))
