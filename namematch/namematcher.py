from dataclasses import dataclass

import re


@dataclass
class Name:
    id: int
    first: str
    middle: list[str]
    nick: str
    last: str
    citizenships: list[str]


@dataclass
class NameMatch:
    name: Name
    label: str
    message: str
    message_offset: int
    start: int
    end: int

    def format(self, emoji):
        return f'{self.message[0:self.start]}{emoji}{self.message[self.start:self.end]}{emoji}{self.message[self.end:]}'.strip()


colon_re = re.compile('(?!\\B\\[[^]]*):(?![^\\[]*]\\B)')
semicolon_re = re.compile('(?!\\B\\[[^]]*);(?![^\\[]*]\\B)')
second_lastname_re = re.compile('[- ](.*)')


class NameMatcher:
    def __init__(self, names: list[Name]):
        self._names_idx = {}
        for n in names:
            self._names_idx[n.id] = n
        self._regex = {'std': NameMatcher.__json_to_regex(names, format='std'),
                      'vd': NameMatcher.__json_to_regex(names, format='vd'),
                      'fr': NameMatcher.__json_to_regex(names, format='fr')}

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

    @staticmethod
    def __last_name_pattern(n):
        if n.startswith('de ') or n.startswith('von '):
            return n
        return second_lastname_re.sub(r'(?:[- ]\1)?', n)

    @staticmethod
    def __expand_with_buergerorte(n, format='std'):
        result = '(?P<_' + str(n.id) + '>'

        lastname = NameMatcher.__last_name_pattern(n.last)
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
            result += '(?:' + lastname + '(?:[- ]\\w+)?, (?:\\w+\\. ?)*\\s?' + firstname + '\\b)'
        elif format == 'vd':
            result += '(?:' + lastname + '(?:(?:\\w+\\. ?)+| )' + firstname + '\\b)'
        elif format == 'fr':
            result += '(?:' + firstname + '(?:(?:\\w+\\. ?)+| )' + lastname + ')'
        else:
            raise Exception(f'Unknown format: {format}')

        if buergerorte:
            if len(buergerorte) > 1:
                result += '[^:;]+?\\b' + '(?:von(?: und in)?|de(?: et à)?|du(?: et au)?|des(?: et aux)?|d\'|d[ia]) (?:' + \
                          '|'.join(buergerorte) + ')'
            else:
                result += '[^:;]+?\\b' + '(?:von(?: und in)?|de(?: et à)?|du(?: et au)?|des(?: et aux)?|d\'|d[ia]) ' + buergerorte[0]

        return result + ')'

    @staticmethod
    def __json_to_regex(names, format='std'):
        r = '(?:^|\\s)(?:' + '|'.join(map(lambda n: NameMatcher.__expand_with_buergerorte(n, format), names)) + ')\\b'
        r = r.replace('Delphine', 'Délphine').replace('Bellaiche', 'Bellaïche').replace('à', '[aà]').replace('á', '[aá]') \
            .replace('ç', '[cç]').replace('é', '[eé]').replace('è', '[eè]').replace('ë', '[eë]').replace('ï', '[iï]') \
            .replace('î', '[iî]').replace('ò', '[oò]').replace('ô', '[oô]')
        # if format == 'std':
        #     print(r)
        return re.compile(r, re.UNICODE)

    def __repr__(self):
        return str(self._names_idx)

    def __str__(self):
        return str(self._names_idx)
