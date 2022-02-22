create table shab_match_job
(
    id          int       not null auto_increment primary key,
    started_at  timestamp not null default current_timestamp,
    finished_at timestamp null,
    from_date   date      not null,
    to_date     date      not null
);

create table shab_name_match
(
    job_id            int          not null references shab_match_job (id),
    company_name      varchar(255) not null,
    uid               varchar(15)  not null,
    reg_company_url   varchar(255) not null,
    publ_id           int          not null,
    publ_url          varchar(255) not null,
    canton            varchar(2)   not null,
    journal_date      date         not null,
    publ_date         date         not null,
    parlamentarier_id int references parlamentarier (id),
    person_id         int references person (id),
    label             varchar(255) not null,
    offset            int          not null,
    extract           mediumtext   not null,
    mutations         json         not null
);

create table sheets_query
(
    query_set  varchar(100) not null,
    sheet_name varchar(100) not null,
    query      mediumtext   not null
);

create table website
(
    id         int          not null auto_increment primary key,
    url        varchar(255) not null,
    created_at timestamp    not null default current_timestamp,
    updated_at timestamp    not null default current_timestamp,
    unique (url)
);

create table website_link
(
    id              int       not null auto_increment primary key,
    from_website_id int       not null references website (id),
    to_webpage_id   int       not null references website (id),
    created_at      timestamp not null default current_timestamp,
    unique (from_website_id, to_webpage_id)
);

create table webpage
(
    id           int          not null auto_increment primary key,
    website_id   int          not null references website (id),
    path         varchar(400) not null,
    sha1         varchar(40)  not null,
    etag         varchar(400),
    created_at   timestamp    not null default current_timestamp,
    last_crawled timestamp,
    unique (website_id, path)
);

drop table webpage;

create table webpage_match
(
    id                int          not null auto_increment primary key,
    webpage_id        int          not null references webpage (id),
    parlamentarier_id int references parlamentarier (id),
    person_id         int references person (id),
    offset            int          not null,
    extract           varchar(100),
    created_at        timestamp    not null default current_timestamp
);

drop table webpage_match;

create or replace view v_abgegrenzte_interessenbindung
as
with parlamentarier_amtszeit as (
    select pa.*, im_rat_seit von_effektiv, coalesce(im_rat_bis, date '9999-12-31') bis_effektiv
    from parlamentarier pa
    where ratsunterbruch_von is null
    union all
    select *
    from parlamentarier pa
             cross join lateral ( select pa.im_rat_seit von_effektiv, pa.ratsunterbruch_von bis_effektiv
                                  union all
                                  select pa.ratsunterbruch_bis, coalesce(im_rat_bis, date '9999-12-31')) as t
    where ratsunterbruch_von is not null
      and ratsunterbruch_bis is not null
),
     interessebindungen_mit_erstrecherche as (
         select min(i.freigabe_datum) over (partition by parlamentarier_id) erstrecherche, i.*
         from interessenbindung i
         where i.freigabe_datum is not null
     )
select i.parlamentarier_id,
       pa.vorname,
       pa.nachname,
       i.erstrecherche,
       i.id                                                                                                                                                      interessebindung_id,
       cast(greatest(coalesce(i.von, date '0000-01-01'), pa.von_effektiv,
                     IF(i.erstrecherche = i.freigabe_datum, pa.von_effektiv, coalesce(i.von,
                                                                                      IF(i.bis < i.freigabe_datum, pa.im_rat_seit, i.freigabe_datum)))) as date) von_effektiv,
       cast(least(coalesce(i.bis, date '9999-12-31'), pa.bis_effektiv) as date)                                                                                  bis_effektiv,
       i.art,
       i.funktion_im_gremium,
       i.deklarationstyp,
       i.status,
       i.organisation_id,
       o.name_de,
       o.rechtsform,
       o.vernehmlassung
from interessebindungen_mit_erstrecherche i
         join parlamentarier_amtszeit pa on pa.id = i.parlamentarier_id
         join organisation o on i.organisation_id = o.id
    and von_effektiv <= coalesce(bis, date '9999-12-31')
    and coalesce(bis_effektiv, date '9999-12-31') > coalesce(von, i.freigabe_datum)
where i.freigabe_datum is not null
;

create table translations
as
select s.location context, s.field item, s.source de, t.translation fr
from lobbywat_lobbywatch.translation_source s
         join lobbywat_lobbywatch.translation_target t on t.translation_source_id = s.id
where 1=1
  and s.textgroup = 'default'
  and s.location in ('organisation', 'interessenbindung', 'mandat', 'parlamentarier', 'zutrittsberechtigung', 'kommission', 'partei', 'fraktion')
  and s.field not in ('beruf', 'arbeitssprache')
  and t.lang = 'fr'
;
ALTER TABLE translations convert to CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
;
