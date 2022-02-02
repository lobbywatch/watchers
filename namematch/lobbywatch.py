from enum import Enum
from .namematcher import Name, NameMatcher


class PersonType(Enum):
    PARLIAMENTARIAN = '🙋️'
    LOBBYIST = '👻'

    def __init__(self, emoji):
        self.emoji = emoji


def create_parliamentarian_matcher(mycursor, ref_date):
    mycursor.execute('''
        select distinct id, vorname, zweiter_vorname, vorname_kurz, nachname, buergerorte
        from parlamentarier pa
        where exists (
            select null
            from in_rat
            where parlamentarier_id = pa.id
            and coalesce(bis, now()) >= now()
        )
        order by 1, 3
    ''', {'date': ref_date})
    names = []
    for row in mycursor.fetchall():
        if row[0] == 357:
            n = Name((PersonType.PARLIAMENTARIAN, row[0]), 'Nicole Melanie',
                     tuple(row[2].split(' ')) if row[2] else None, row[3], row[4],
                     tuple(row[5].split(';')) if row[5] else None)
        elif row[0] == 383:
            n = Name((PersonType.PARLIAMENTARIAN, row[0]), row[1],
                                 tuple(row[2].split(' ')) if row[2] else None, row[3], row[4],
                                 tuple((row[5] + ';Randogne').split(';')))
        else:
            n = Name((PersonType.PARLIAMENTARIAN, row[0]), row[1], tuple(row[2].split(' ')) if row[2] else None, row[3],
                                 row[4], tuple(row[5].split(';')) if row[5] else None)
        names.append(n)
    return NameMatcher(names=names)


def create_lobbyist_matcher(mycursor, ref_date):
    mycursor.execute('''
        select distinct p.id, p.vorname, p.zweiter_vorname, p.vorname_kurz, p.nachname, p.buergerorte
        from person p
         join zutrittsberechtigung z on p.id = z.person_id
         join parlamentarier pa on z.parlamentarier_id = pa.id
        where coalesce(z.bis, now()) >= now()
          and coalesce(pa.im_rat_bis, now()) >= now()
          and coalesce(p.buergerorte, '') != 'Unbekannt'
        order by 1, 3
    ''', {'date': ref_date})
    names = []
    for row in mycursor.fetchall():
        if row[0] == 301:
            n = Name((PersonType.LOBBYIST, row[0]), '(?:Christian|Karoly)', None, None, 'K(?:o|ö)pe',
                                 tuple(row[5].split(';')) if row[5] else None)
        else:
            n = Name((PersonType.LOBBYIST, row[0]), row[1], tuple(row[2].split(' ')) if row[2] else None, row[3],
                                 row[4], tuple(row[5].split(';')) if row[5] else None)
        names.append(n)
    return NameMatcher(names=names)


def create_matchers_from_database(cursor, ref_date):
    return [create_parliamentarian_matcher(cursor, ref_date), create_lobbyist_matcher(cursor, ref_date)]
