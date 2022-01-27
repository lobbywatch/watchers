from dataclasses import dataclass
from typing import Any

import regex as re


# AnyStr = str | bytes


@dataclass(frozen=True)
class Name:
    id: Any
    first: str
    middle: tuple[str, ...]
    nick: str
    last: str
    citizenships: tuple[str, ...]


@dataclass(frozen=True)
class NameMatch:
    name: Name
    label: bytes # AnyStr
    message: bytes # AnyStr
    message_offset: int
    start: int
    end: int

    def format(self, emoji):
        return f'{str(self.message[0:self.start], "utf-8")}{emoji}{str(self.message[self.start:self.end], "utf-8")}{emoji}{str(self.message[self.end:], "utf-8")}'.strip()


colon_re = re.compile(b'(?!\\B\\[[^]]*):(?![^\\[]*]\\B)')
semicolon_re = re.compile(b'(?!\\B\\[[^]]*);(?![^\\[]*]\\B)')
second_lastname_re = re.compile('[- ](.*)')


class NameMatcher:
    def __init__(self, names: list[Name]):
        self._names_idx = {}
        for idx, n in enumerate(names):
            self._names_idx[idx] = n
            self._names_idx[n] = idx
        self._regex = {'std': self.__json_to_regex(names, format='std'),
                      'vd': self.__json_to_regex(names, format='vd'),
                      'fr': self.__json_to_regex(names, format='fr')}

    def regex(self, format='std'):
        return self._regex[format]

    def match(self, message, format='std'):
        res = []
        for m in self._regex[format].finditer(message):
            for i in m.groupdict().items():
                if i[1]:
                    name = self._names_idx[int(i[0][1:])]
                    semi_match = list(semicolon_re.finditer(message[0:m.start(i[0])]))
                    semi_match = semi_match[-1].start() if semi_match else 0
                    colon_match = list(colon_re.finditer(message[0:m.start(i[0])]))
                    colon_match = colon_match[-1].start() if colon_match else 0
                    start = max(semi_match, colon_match)
                    label = None
                    if message[start] == ';':
                        colon_match = list(colon_re.finditer(message[0:start]))
                        label_end = colon_match[-1].start() if colon_match else 0
                        if label_end > 0:
                            label_start = message.rfind('.', 0, label_end)
                            # if message[label_start + 1:message.find(':', label_start)] != label:
                            label = message[label_start + 1:message.find(':', label_start)].strip()
                        start += 2
                    elif message[start] == ':':
                        label_start = message.rfind('.', 0, start)
                        # if message[label_start + 1:start] != label:
                        label = message[label_start + 1:start].strip()
                        start += 2
                    end = message.find(';', m.end(i[0]))
                    end2 = colon_re.search(message[m.end(i[0]):])
                    if end2:
                        end2 = end2.start() + m.end(i[0])

                    if end == -1 or end2 and end > end2:
                        end = message.rfind('.', m.end(i[0]), end2 if end2 else len(message))
                    if end == -1:
                        end = len(message)
                    start = start if start != -1 else 0
                    res.append(NameMatch(name, label, message[start:end], start, m.start(i[0]) - start, m.end(i[0]) - start))
        return res

    def match_content(self, message, label, offset, format):
        # print(str(label, "utf-8"), str(message, "utf-8"))
        res = []
        matches = semicolon_re.finditer(message)
        regex = self._regex[format]
        try:
            idx = 0
            for match in matches:
                component = message[idx:match.start()]
                self.match_content_component(component, regex, idx, label, offset, res)
                idx = match.end()
            self.match_content_component(message[idx:], regex, idx, label, offset, res)
        except StopIteration:
            pass
        return res

    def match_content_component(self, component, regex, idx, label, offset, res):
        for m in regex.finditer(component):
            # for i, g in enumerate(m.groups()):
                # if g:
                #     res.append(NameMatch(self._names_idx[i], label, component, offset + idx, m.start(i + 1), m.end(i + 1)))
            for i in m.groupdict().items():
                if i[1]:
                    name = self._names_idx[int(i[0][1:])]
                    res.append(NameMatch(name, label, component, offset + idx, m.start(i[0]), m.end(i[0])))

    @staticmethod
    def __last_name_pattern(n):
        if n.startswith('de ') or n.startswith('van ') or n.startswith('De ') or n.startswith('von '):
            return n
        return second_lastname_re.sub('(?:[- ]\1)?', n)

    def __expand_with_buergerorte(self, n, format='std'):
        result = '(?P<_' + str(self._names_idx[n]) + '>'

        lastname = self.__last_name_pattern(n.last)
        firstname = n.first + '(?:' + ' '.join(n.middle) + ')?' if n.middle else n.first
        buergerorte = list(map(lambda o: (o if o.find('(') == -1 else o[0:o.find('(')]).strip(), n.citizenships)) if n.citizenships else []
        if 'Zürich' in buergerorte:
            buergerorte.append('Zurich')
            buergerorte.append('Zurigo')
        if 'Bern' in buergerorte:
            buergerorte.append('Berne')
            buergerorte.append('Berna')
        if 'Basel' in buergerorte:
            buergerorte.append('Bâle')
            buergerorte.append('Basilea')
        if 'Genève' in buergerorte:
            buergerorte.append('Genf')
            buergerorte.append('Ginevra')
        if 'Luzern' in buergerorte:
            buergerorte.append('Lucerne')
            buergerorte.append('Lucerna')
        if 'Neuchâtel' in buergerorte:
            buergerorte.append('Neuenburg')
        if 'Gruyères' in buergerorte:
            buergerorte.append('Greyerz')
        if 'Fribourg' in buergerorte:
            buergerorte.append('Freiburg')
        if 'St. Gallen' in buergerorte:
            buergerorte.append('Saint-Gall')
            buergerorte.append('San Gallo')
        if 'Winterthur' in buergerorte:
            buergerorte.append('Winterthour')
        if 'Biel' in buergerorte:
            buergerorte.append('Biel/Bienne')
            buergerorte.append('Bienne')

        if format == 'std':
            result += '(?:' + lastname + '(?:[- ][^.,;\\- ]+)?, (?:[^.,;\\- ]+\\. ?)*\\s?' + firstname + '(?=[;, ]|$))'
        elif format == 'vd':
            result += '(?:' + lastname + ' (?:[^.,;\\- ]+\\. ?)*' + firstname + '(?=[;, ]|$))'
        elif format == 'fr':
            result += '(?:' + firstname + '(?:(?:[^.,;\\- ]+\\. ?)+| )' + lastname + ')'
        else:
            raise Exception(f'Unknown format: {format}')

        if buergerorte:
            # TODO consider supporting negative lookahead like in `(?!Gaga\b|Gugu\b)`
            if len(buergerorte) > 1:
                result += '[^:;]{0,100}?\\b' + '(?&in) (?:' + '|'.join(buergerorte) + ')'
            else:
                result += '[^:;]{0,100}?\\b' + '(?&in) ' + buergerorte[0]

        return result + ')'

    def __json_to_regex(self, names, format='std'):
        defs = '(?(DEFINE)(?P<in>von(?: und in)?|de(?: et à)?|du(?: et au)?|des(?: et aux)?|d[\'ia]))'
        r = defs + '(?:^|\\s)(?:' + '|'.join(map(lambda n: self.__expand_with_buergerorte(n, format), names)) + ')\\b'
        r = r.replace('Delphine', 'Délphine').replace('Bellaiche', 'Bellaïche').replace('à', '(?:a|à)').replace('á', '(?:a|á)') \
            .replace('ç', '(?:c|ç)').replace('é', '(?:e|é)').replace('è', '(?:e|è)').replace('ë', '(?:e|ë)') \
            .replace('ï', '(?:i|ï)').replace('î', '(?:i|î)').replace('ò', '(?:o|ò)').replace('ô', '(?:o|ô)')
        # if format == 'std':
        #     print(r)
        return re.compile(r.encode('utf-8'))

    def __repr__(self):
        return str(self._names_idx)

    def __str__(self):
        return str(self._names_idx)
