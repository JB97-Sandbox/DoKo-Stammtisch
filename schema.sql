-- Supabase / PostgreSQL Schema fuer Stammtisch Punkte-Tracker

create table spieler (
    id bigint generated always as identity primary key,
    name text not null unique
);

create table spielabend (
    id bigint generated always as identity primary key,
    datum date not null,
    ort text
);

create table spiel (
    id bigint generated always as identity primary key,
    spielabend_id bigint references spielabend(id) on delete cascade,
    spielart text not null check (spielart in ('Doppelkopf', 'Skat')),
    runde int not null default 1
);

create table ergebnis (
    id bigint generated always as identity primary key,
    spiel_id bigint references spiel(id) on delete cascade,
    spieler_id bigint references spieler(id) on delete cascade,
    punkte int not null default 0
);

-- Row Level Security aktivieren, aber offen fuer anon key (App-Passwort schuetzt stattdessen)
alter table spieler enable row level security;
alter table spielabend enable row level security;
alter table spiel enable row level security;
alter table ergebnis enable row level security;

create policy "allow all spieler" on spieler for all using (true) with check (true);
create policy "allow all spielabend" on spielabend for all using (true) with check (true);
create policy "allow all spiel" on spiel for all using (true) with check (true);
create policy "allow all ergebnis" on ergebnis for all using (true) with check (true);
