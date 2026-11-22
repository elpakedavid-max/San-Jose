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
  dt          text,                    -- (sin uso: ya no se pide documento)
  img         boolean not null default false,  -- permiso de imagen
  avisos      boolean not null default true,
  hijo        text,                    -- nombre del hijo/a que indica la familia al registrarse
  approved    boolean not null default false,
  admin       boolean not null default false,  -- administrador del programa (valida altas)
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
  select exists (select 1 from profiles where id = auth.uid() and approved and (role = 'entrenador' or admin));
$$;

-- Nadie se aprueba a sí mismo. Si no hay ningún entrenador ni administrador, el primer
-- entrenador que se registra queda aprobado; a partir de ahí, los administradores aprueban.
-- Para nombrar administrador desde el panel: update profiles set admin = true, approved = true where email = '...';
create or replace function public.profiles_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then          -- cambios hechos desde el panel de Supabase
    return new;
  end if;
  if tg_op = 'INSERT' then
    new.admin := false;
    new.approved := (new.role = 'entrenador'
      and not exists (select 1 from profiles where approved and (role = 'entrenador' or admin)));
  elsif not public.is_staff() then
    new.approved := old.approved;
    new.role := old.role;
    new.admin := old.admin;
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


-- ---------- Chat ----------
create table if not exists public.messages (
  id          bigint generated always as identity primary key,
  channel     text not null check (channel = 'grupo' or channel like 'dm:%'),  -- 'grupo' o 'dm:<id de la familia>'
  author      uuid default auth.uid() references auth.users on delete set null,
  author_name text,
  author_info text,
  body        text not null check (char_length(body) between 1 and 2000),
  created_at  timestamptz not null default now()
);
alter table public.messages add column if not exists audio text;
alter table public.messages add column if not exists dur int;
create index if not exists messages_channel_created on public.messages (channel, created_at desc);
alter table public.messages enable row level security;
create or replace function public.messages_guard() returns trigger
language plpgsql security definer set search_path = public as $$
declare p record;
begin
  select pr.nombre, pr.apellidos, pr.role, pr.cargo, pr.admin, pl.n as hijo
    into p from profiles pr left join players pl on pl.id = pr.pid where pr.id = auth.uid();
  new.author := auth.uid();
  new.created_at := now();
  new.author_name := coalesce(p.nombre,'') || coalesce(' ' || left(p.apellidos,1) || '.', '');
  new.author_info := case
    when p.role = 'entrenador' then coalesce(nullif(p.cargo,''), 'Entrenador')
    when p.role = 'familiar' and p.hijo is not null then 'Familia de ' || p.hijo
    when p.role = 'jugador' then 'Jugador'
    when p.admin then 'Administración'
    else coalesce(nullif(p.cargo,''), 'Club') end;
  return new;
end $$;
drop trigger if exists messages_guard on public.messages;
create trigger messages_guard before insert on public.messages for each row execute function public.messages_guard();
revoke execute on function public.messages_guard() from public, anon, authenticated;
drop policy if exists "leer chat" on public.messages;
create policy "leer chat" on public.messages for select using (
  public.is_member() and (channel = 'grupo' or channel = 'dm:' || auth.uid()::text or public.is_staff()));
drop policy if exists "escribir chat" on public.messages;
create policy "escribir chat" on public.messages for insert with check (
  public.is_member() and (channel = 'grupo' or channel = 'dm:' || auth.uid()::text or (public.is_staff() and channel like 'dm:%')));
drop policy if exists "borrar chat" on public.messages;
create policy "borrar chat" on public.messages for delete using (author = auth.uid() or public.is_staff());
grant select, insert, delete on public.messages to authenticated;
revoke all on public.messages from anon;

-- ---------- Fotos de perfil ----------
alter table public.profiles add column if not exists avatar text;
create or replace function public.member_cards()
returns table (id uuid, name text, info text, avatar text)
language sql stable security definer set search_path = public as $$
  select pr.id, pr.nombre || coalesce(' ' || left(pr.apellidos,1) || '.', ''),
         case when pr.role = 'entrenador' then coalesce(nullif(pr.cargo,''),'Entrenador')
              when pr.role = 'familiar' and pl.n is not null then 'Familia de ' || pl.n
              when pr.role = 'jugador' then 'Jugador'
              else coalesce(nullif(pr.cargo,''),'Club') end,
         pr.avatar
  from profiles pr left join players pl on pl.id = pr.pid
  where pr.approved and public.is_member();
$$;
revoke execute on function public.member_cards() from public, anon;
grant execute on function public.member_cards() to authenticated;

-- ---------- Tiempo real (marcador en directo) ----------
do $$
declare t text;
begin
  foreach t in array array['profiles','players','matches','ratings','trainings','settings','media','messages'] loop
    if not exists (select 1 from pg_publication_tables
                   where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = t) then
      execute format('alter publication supabase_realtime add table public.%I', t);
    end if;
  end loop;
end $$;

-- ---------- Fotos y vídeos ----------
create table if not exists public.media (
  id            bigint primary key,
  path          text not null,
  thumb         text,
  kind          text not null check (kind in ('foto','video')),
  match_id      bigint references public.matches on delete set null,
  caption       text,
  uploader      uuid default auth.uid() references auth.users on delete set null,
  uploader_name text,
  approved      boolean not null default false,   -- lo de las familias espera a que lo apruebe un administrador
  created_at    timestamptz not null default now()
);
alter table public.media enable row level security;

create or replace function public.media_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' then
    new.uploader := auth.uid();
    new.approved := public.is_staff();
    new.created_at := now();
  elsif not public.is_staff() then
    new.approved := old.approved;
    new.uploader := old.uploader;
  end if;
  return new;
end $$;
drop trigger if exists media_guard on public.media;
create trigger media_guard before insert or update on public.media
  for each row execute function public.media_guard();

drop policy if exists "ver media" on public.media;
create policy "ver media" on public.media for select
  using (public.is_staff() or (public.is_member() and (approved or uploader = auth.uid())));
drop policy if exists "subir media" on public.media;
create policy "subir media" on public.media for insert with check (public.is_member());
drop policy if exists "editar media" on public.media;
create policy "editar media" on public.media for update using (public.is_staff() or uploader = auth.uid());
drop policy if exists "borrar media" on public.media;
create policy "borrar media" on public.media for delete using (public.is_staff() or uploader = auth.uid());
grant select, insert, update, delete on public.media to authenticated;
revoke all on public.media from anon;
revoke execute on function public.media_guard() from public, anon, authenticated;

-- Almacenamiento privado (máx. 50 MB por archivo: límite del plan gratis)
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('media', 'media', false, 52428800, array['image/*','video/*','audio/*'])
on conflict (id) do update set public = false, file_size_limit = 52428800, allowed_mime_types = array['image/*','video/*','audio/*'];
drop policy if exists "sj media leer" on storage.objects;
create policy "sj media leer" on storage.objects for select to authenticated
  using (bucket_id = 'media' and public.is_member());
drop policy if exists "sj media subir" on storage.objects;
create policy "sj media subir" on storage.objects for insert to authenticated
  with check (bucket_id = 'media' and public.is_member() and (storage.foldername(name))[1] = auth.uid()::text);
drop policy if exists "sj media borrar" on storage.objects;
create policy "sj media borrar" on storage.objects for delete to authenticated
  using (bucket_id = 'media' and (public.is_staff() or owner_id = auth.uid()::text));

-- ---------- Temporadas ----------
alter table public.matches   add column if not exists season text;
alter table public.trainings add column if not exists season text;
alter table public.media     add column if not exists season text;
alter table public.players   add column if not exists seasons text[] not null default '{}';
insert into public.settings (key, value) values ('seasons', '["2026/27"]'), ('season', '2026/27')
on conflict (key) do nothing;

-- ---------- Plantilla inicial · Estrellitas ----------
insert into public.players (id, n, p, dem, pie, cual, seasons) values
  (1,  'Raúl',           'POR', 'Portero',                                'Diestro', null, array['2026/27']),
  (2,  'Gonzalo',        'DEF', 'Lateral izquierdo',                      'Zurdo',   'Rápido y con buena pegada.', array['2026/27']),
  (3,  'Lucas',          'DEF', 'Central',                                'Diestro', 'Muy regular y con buena pegada de balón.', array['2026/27']),
  (4,  'Adri',           'MED', 'Banda derecha',                          'Diestro', 'Rápido y muy escurridizo.', array['2026/27']),
  (5,  'Tadeuz',         'MED', 'Mediocentro',                            'Diestro', 'Muy técnico, buena pegada al balón, goleador y luchador.', array['2026/27']),
  (6,  'Nico',           'DEL', 'Delantero',                              'Diestro', 'Aguanta muy bien el balón, buen pase y buena pegada. Goleador.', array['2026/27']),
  (7,  'Guille',         'DEL', 'Banda y delantero',                      'Diestro', 'Rápido y con buena conducción del balón.', array['2026/27']),
  (8,  'Gonzalo Sancho', 'DEL', 'Delantero',                              'Diestro', 'Rápido y luchador.', array['2026/27']),
  (9,  'Vitorio',        'MED', 'Centro del campo y delantero',           'Diestro', 'Luchador y con buena conducción del balón.', array['2026/27']),
  (10, 'Elías',          'DEL', 'Delantero',                              'Diestro', 'Alto y rápido.', array['2026/27']),
  (11, 'Blake',          'DEF', 'Defensa',                                'Diestro', 'Muy luchador y rápido.', array['2026/27']),
  (12, 'Ale',            'DEF', 'Defensa',                                'Diestro', 'Muy rápido, mete mucho la pierna y va bien al choque.', array['2026/27']),
  (13, 'Christofer',     'MED', 'Interior por banda izquierda o derecha', 'Diestro', 'Muy rápido conduciendo la pelota.', array['2026/27']),
  (14, 'Enrico',         'DEL', 'Delantero',                              'Diestro', 'Muy habilidoso y rápido.', array['2026/27'])
on conflict (id) do nothing;
