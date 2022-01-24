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
    publ_id           int          not null,
    publ_url          varchar(255) not null,
    canton            varchar(2)   not null,
    journal_date      date         not null,
    publ_date         date         not null,
    parlamentarier_id int references parlamentarier (id),
    person_id         int references person (id),
    label             varchar(255) not null,
    offset            int          not null,
    extract           mediumtext   not null
);
