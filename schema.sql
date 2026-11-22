-- =====================================================================
-- San José · Estrellitas — base de datos (Supabase)
-- Pega este archivo entero en Supabase → SQL Editor → Run.
-- Se puede ejecutar más de una vez sin romper nada.
-- =====================================================================

-- ---------- Tablas ----------
create table if not exists public.profiles (
  id          uuid primary key references auth.users on delete cascade,
  nombre      text not null,
  apellidos   text not null,
  nac         date,
  tel         text,
  email       text,
  role        text not null check (role in ('entrenador','jugador','familiar','otro')),
  cargo       text,
  cat         text,
  pid         bigint,
  rel         text,
  dt          text,                    -- tipo de documento (el número NO se guarda)
  img         boolean not null default false,  -- permiso de imagen
  avisos      boolean not null default true,
  approved    boolean not null default false,
  created_at  timestamptz not null default now()
);

create table if not exists public.players (
  id    bigint primary key,
  n     text not null,
  p     text not null check (p in ('POR','DEF','MED','DEL')),
  d     int check (d between 1 and 99),
  dem   text,
  pie   text,
  cual  text
);

create table if not exists public.matches (
  id      bigint primary key,
  rival   text not null,
  fecha   date not null,
  local   boolean not null default true,
  dur     int not null default 50,
  estado  text not null default 'prox' check (estado in ('prox','live','fin')),
  tit     bigint[] not null default '{}',
  ev      jsonb not null default '[]',
  acc     double precision not null default 0,
  run     bigint,
  video   text
);

create table if not exists public.ratings (   -- valoraciones: solo las ve el entrenador
  match_id  bigint references public.matches on delete cascade,
  player_id bigint references public.players on delete cascade,
  nota      int not null check (nota between 1 and 10),
  primary key (match_id, player_id)
);

create table if not exists public.trainings (
  id     bigint primary key,
  fecha  date not null,
  pr     bigint[] not null default '{}'
);

create table if not exists public.settings (
  key    text primary key,
  value  text
);

-- ---------- Quién es quién ----------
create or replace function public.is_member() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from profiles where id = auth.uid() and approved);
$$;

create or replace function public.is_staff() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from profiles where id = auth.uid() and approved and role = 'entrenador');
$$;

-- Nadie se aprueba a sí mismo. El primer entrenador que se registra queda
-- aprobado automáticamente; a partir de ahí, él aprueba al resto.
create or replace function public.profiles_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' then
    new.approved := (new.role = 'entrenador'
      and not exists (select 1 from profiles where approved and role = 'entrenador'));
  elsif not public.is_staff() then
    new.approved := old.approved;
    new.role := old.role;
  end if;
  return new;
end $$;

drop trigger if exists profiles_guard on public.profiles;
create trigger profiles_guard before insert or update on public.profiles
  for each row execute function public.profiles_guard();

-- ---------- Seguridad (RLS) ----------
alter table public.profiles  enable row level security;
alter table public.players   enable row level security;
alter table public.matches   enable row level security;
alter table public.ratings   enable row level security;
alter table public.trainings enable row level security;
alter table public.settings  enable row level security;

drop policy if exists "perfil propio o entrenador ve" on public.profiles;
create policy "perfil propio o entrenador ve" on public.profiles
  for select using (id = auth.uid() or public.is_staff());
drop policy if exists "crear mi perfil" on public.profiles;
create policy "crear mi perfil" on public.profiles
  for insert with check (id = auth.uid());
drop policy if exists "editar perfil" on public.profiles;
create policy "editar perfil" on public.profiles
  for update using (id = auth.uid() or public.is_staff());
drop policy if exists "borrar perfil" on public.profiles;
create policy "borrar perfil" on public.profiles
  for delete using (id = auth.uid() or public.is_staff());

do $$
declare t text;
begin
  foreach t in array array['players','matches','trainings','settings'] loop
    execute format('drop policy if exists "miembros leen" on public.%I', t);
    execute format('create policy "miembros leen" on public.%I for select using (public.is_member())', t);
    execute format('drop policy if exists "entrenador escribe" on public.%I', t);
    execute format('create policy "entrenador escribe" on public.%I for all using (public.is_staff()) with check (public.is_staff())', t);
  end loop;
end $$;

drop policy if exists "solo entrenador" on public.ratings;
create policy "solo entrenador" on public.ratings
  for all using (public.is_staff()) with check (public.is_staff());

revoke all on all tables in schema public from anon;
grant select, insert, update, delete on all tables in schema public to authenticated;
revoke execute on function public.is_member(), public.is_staff(), public.profiles_guard() from public, anon;
revoke execute on function public.profiles_guard() from authenticated;
grant execute on function public.is_member(), public.is_staff() to authenticated;

-- ---------- Tiempo real (marcador en directo) ----------
do $$
declare t text;
begin
  foreach t in array array['profiles','players','matches','ratings','trainings','settings'] loop
    if not exists (select 1 from pg_publication_tables
                   where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = t) then
      execute format('alter publication supabase_realtime add table public.%I', t);
    end if;
  end loop;
end $$;

-- ---------- Plantilla inicial · Estrellitas ----------
insert into public.players (id, n, p, dem, pie, cual) values
  (1,  'Raúl',           'POR', 'Portero',                                'Diestro', null),
  (2,  'Gonzalo',        'DEF', 'Lateral izquierdo',                      'Zurdo',   'Rápido y con buena pegada.'),
  (3,  'Lucas',          'DEF', 'Central',                                'Diestro', 'Muy regular y con buena pegada de balón.'),
  (4,  'Adri',           'MED', 'Banda derecha',                          'Diestro', 'Rápido y muy escurridizo.'),
  (5,  'Tadeo',          'MED', 'Mediocentro',                            'Diestro', 'Muy técnico, buena pegada al balón, goleador y luchador.'),
  (6,  'Nico',           'DEL', 'Delantero',                              'Diestro', 'Aguanta muy bien el balón, buen pase y buena pegada. Goleador.'),
  (7,  'Guille',         'DEL', 'Banda y delantero',                      'Diestro', 'Rápido y con buena conducción del balón.'),
  (8,  'Gonzalo Sancho', 'DEL', 'Delantero',                              'Diestro', 'Rápido y luchador.'),
  (9,  'Vitorio',        'MED', 'Centro del campo y delantero',           'Diestro', 'Luchador y con buena conducción del balón.'),
  (10, 'Elías',          'DEL', 'Delantero',                              'Diestro', 'Alto y rápido.'),
  (11, 'Blake',          'DEF', 'Defensa',                                'Diestro', 'Muy luchador y rápido.'),
  (12, 'Ale',            'DEF', 'Defensa',                                'Diestro', 'Muy rápido, mete mucho la pierna y va bien al choque.'),
  (13, 'Christofer',     'MED', 'Interior por banda izquierda o derecha', 'Diestro', 'Muy rápido conduciendo la pelota.'),
  (14, 'Enrico',         'DEL', 'Delantero',                              'Diestro', 'Muy habilidoso y rápido.')
on conflict (id) do nothing;
