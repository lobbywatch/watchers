from enum import Enum
from .namematcher import Name, NameMatcher


class NameSet(Enum):
    CURRENT = 1
    RESEARCH = 2


class PersonType(Enum):
    PARLIAMENTARIAN = '🙋️'
    LOBBYIST = '👻'
    OTHER = '👑'

    def __init__(self, emoji):
        self.emoji = emoji


def create_parliamentarian_names(mycursor, ref_date, name_set):
    mycursor.execute('''
        select distinct id, vorname, zweiter_vorname, vorname_kurz, nachname, buergerorte
        from parlamentarier pa
        # where exists (
        #     select null
        #     from in_rat
        #     where parlamentarier_id = pa.id
        #     and coalesce(bis, now()) >= now()
        # )
        where coalesce(im_rat_bis, now()) >= now()
          and (%(match_current)s or pa.freigabe_datum is null) 
        order by 1, 3
    ''', {'date': ref_date, 'match_current': name_set == NameSet.CURRENT})
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
    return names


def create_lobbyist_names(mycursor, ref_date, name_set):
    mycursor.execute('''
        select distinct p.id, p.vorname, nullif(p.zweiter_vorname, '') zweiter_vorname, p.vorname_kurz, p.nachname, p.buergerorte
        from person p
         join zutrittsberechtigung z on p.id = z.person_id
         join parlamentarier pa on z.parlamentarier_id = pa.id
        where coalesce(z.bis, now()) >= now()
          and coalesce(pa.im_rat_bis, now()) >= now()
          and coalesce(p.buergerorte, '') != 'Unbekannt'
          and (%(match_current)s or p.freigabe_datum is null) 
        order by 1, 3
    ''', {'date': ref_date, 'match_current': name_set == NameSet.CURRENT})
    names = []
    for row in mycursor.fetchall():
        if row[0] == 301:
            n = Name((PersonType.LOBBYIST, row[0]), '(?:Christian|Karoly)', None, None, 'K(?:o|ö)pe',
                     tuple(row[5].split(';')) if row[5] else None)
        else:
            n = Name((PersonType.LOBBYIST, row[0]), row[1], tuple(row[2].split(' ')) if row[2] else None, row[3],
                     row[4], tuple(row[5].split(';')) if row[5] else None)
        names.append(n)
    return names


def create_matchers_from_database(cursor, ref_date, name_set=NameSet.CURRENT):
    if name_set == NameSet.CURRENT:
        return [NameMatcher(create_parliamentarian_names(cursor, ref_date, name_set)),
                NameMatcher(create_lobbyist_names(cursor, ref_date, name_set))]
    else:
        return [NameMatcher(
            create_parliamentarian_names(cursor, ref_date, name_set) + create_lobbyist_names(cursor, ref_date, name_set))]


def is_ambiguous_name(name):
    # 383: christophe clivaz
    # 807: michel rudin
    # 963: matthias müller
    # 329: irène kälin
    return type(name.id) is tuple and name.id in (
        (PersonType.PARLIAMENTARIAN, 383), (PersonType.LOBBYIST, 807), (PersonType.LOBBYIST, 963),
        (PersonType.PARLIAMENTARIAN, 329),
    )
