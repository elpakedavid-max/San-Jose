// PostgreSQL aislado (PGlite); no se conecta a Supabase ni usa datos reales.
// npm install --no-save --package-lock=false --ignore-scripts @electric-sql/pglite@0.3.14
// node tests/test_schema.mjs
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { PGlite } from '@electric-sql/pglite';

const db = new PGlite();
const ids = {
  staff: '00000000-0000-4000-8000-000000000001',
  family: '00000000-0000-4000-8000-000000000002',
  peer: '00000000-0000-4000-8000-000000000003',
  pending: '00000000-0000-4000-8000-000000000004',
  signup: '00000000-0000-4000-8000-000000000005'
};
const file = (who, leaf) => `${ids[who]}/${leaf}`;
async function as(who, sql, params = []) {
  await db.exec('set role authenticated');
  await db.query("select set_config('request.jwt.claim.sub', $1, false)", [ids[who]]);
  try { return await db.query(sql, params); }
  finally {
    await db.exec('reset role');
    await db.exec("select set_config('request.jwt.claim.sub', '', false)");
  }
}
async function visible(who, path) {
  const r = await as(who, 'select name from storage.objects where name = $1', [path]);
  return r.rows.length === 1;
}

try {
  // Solo se simula la infraestructura de Supabase, no sus tablas ni políticas de app.
  await db.exec(`
    create role anon nologin;
    create role authenticated nologin;
    create schema auth;
    create table auth.users (id uuid primary key, last_sign_in_at timestamptz,
      created_at timestamptz default now());
    create function auth.uid() returns uuid language sql stable as $$
      select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid;
    $$;
    create schema storage;
    create table storage.buckets (id text primary key, name text, public boolean,
      file_size_limit bigint, allowed_mime_types text[]);
    create table storage.objects (id bigint generated always as identity primary key,
      bucket_id text references storage.buckets, name text, owner_id text);
    create function storage.foldername(name text) returns text[] language sql as $$
      select (string_to_array(name, '/'))[1:array_length(string_to_array(name, '/'),1)-1];
    $$;
    alter table storage.objects enable row level security;
    grant usage on schema public, auth, storage to authenticated, anon;
    grant select, insert, delete on storage.objects to authenticated;
    create publication supabase_realtime;
  `);
  const schema = await readFile(new URL('../schema.sql', import.meta.url), 'utf8');
  await db.exec(schema);
  await db.exec(schema);
  console.log('OK: instalación desde cero y segunda ejecución completa');
  // Se eliminan las semillas existentes; todas las pruebas usan jugadores inventados.
  await db.exec('delete from public.players');
  for (const id of Object.values(ids)) await db.query('insert into auth.users(id) values ($1)', [id]);
  // Ni el primer entrenador puede darse permisos desde el registro público.
  await as('staff', `insert into public.profiles(id,nombre,apellidos,role,approved,admin)
    values (auth.uid(),'Técnico','Prueba','entrenador',true,true)`);
  const first = (await as('staff', 'select approved,admin from profiles where id=auth.uid()')).rows[0];
  assert.equal(first.approved, false);
  assert.equal(first.admin, false);
  assert.equal((await as('staff', 'select public.is_staff() as staff')).rows[0].staff, false);
  assert.equal((await as('staff', 'select * from players')).rows.length, 0);
  await assert.rejects(as('staff', `insert into players(id,n,p) values(100,'Prueba','MED')`), /row-level security/);
  // Alta inicial hecha desde el panel privado, identificado por UUID.
  await db.query('update profiles set approved=true,admin=true where id=$1', [ids.staff]);
  for (const who of ['family', 'peer', 'pending']) {
    await as(who, `insert into public.profiles(id,nombre,apellidos,role,pid)
      values (auth.uid(),'Familiar','Prueba','familiar',101)`);
  }
  await db.exec(`insert into public.players(id,n,p) values
    (101,'Jugador de prueba A','MED'),(102,'Jugador de prueba B','DEF')`);
  await as('staff', 'update public.profiles set approved=true,pid=101 where id=$1', [ids.family]);
  await as('staff', 'update public.profiles set approved=true,pid=102 where id=$1', [ids.peer]);
  const pending = await as('pending', 'select pid from public.profiles where id=auth.uid()');
  assert.equal(pending.rows[0].pid, null, 'el registro no elige su propia vinculación');
  await as('family', `update public.profiles set pid=102,role='entrenador',admin=true,
    nombre='Nombre editable' where id=auth.uid()`);
  const profile = (await as('family', 'select * from public.profiles where id=auth.uid()')).rows[0];
  assert.equal(Number(profile.pid), 101);
  assert.equal(profile.role, 'familiar');
  assert.equal(profile.admin, false);
  assert.equal(profile.nombre, 'Nombre editable');
  await as('signup', `insert into public.profiles(id,nombre,apellidos,role,pid)
    values(auth.uid(),'Alta','Prueba','familiar',102)`);
  assert.equal((await as('signup', 'select pid from profiles where id=auth.uid()')).rows[0].pid, null);
  await as('staff', 'update public.profiles set pid=102 where id=$1', [ids.family]);
  assert.equal(Number((await as('family', 'select pid from profiles where id=auth.uid()')).rows[0].pid), 102);
  await as('staff', 'update public.profiles set pid=101 where id=$1', [ids.family]);
  await assert.rejects(as('family', 'select public.set_child_photo(102,$1)', [file('family','child.jpg')]), /Solo puedes/);
  await assert.rejects(as('family', 'select public.set_child_photo(101,$1)', [file('peer','child.jpg')]), /Archivo no válido/);
  await as('family', 'select public.set_child_photo(101,$1)', [file('family','child.jpg')]);
  await as('family', 'select public.set_child_photo(101,null)');
  await as('family', 'select public.set_child_photo(101,$1)', [file('family','child.jpg')]);
  console.log('OK: solo el cuerpo técnico cambia pid; la familia conserva sus permisos de foto');

  await db.exec('grant usage on all sequences in schema public, storage to authenticated');
  const objects = [
    ['family','pending.jpg'], ['family','approved.jpg'], ['family','thumb.jpg'],
    ['family','private.webm'], ['staff','reply.webm'], ['peer','group.webm'],
    ['family','child.jpg'], ['family','avatar.jpg'], ['staff','staff.jpg'],
    ['family','orphan.jpg'], ['pending','avatar.jpg']
  ];
  for (const [who, leaf] of objects) {
    await db.query("insert into storage.objects(bucket_id,name,owner_id) values('media',$1,$2)",
      [file(who,leaf), ids[who]]);
  }
  await as('family', `insert into public.media(id,path,kind) values (201,$1,'foto'),(202,$2,'foto')`,
    [file('family','pending.jpg'),file('family','approved.jpg')]);
  await as('staff', 'update public.media set approved=true,thumb=$1 where id=202', [file('family','thumb.jpg')]);
  await as('family', `insert into public.messages(channel,body,audio) values ($1,'Audio de prueba',$2)`,
    [`dm:${ids.family}`,file('family','private.webm')]);
  await as('staff', `insert into public.messages(channel,body,audio) values ($1,'Respuesta de prueba',$2)`,
    [`dm:${ids.family}`,file('staff','reply.webm')]);
  await as('peer', `insert into public.messages(channel,body,audio) values ('grupo','Audio de grupo',$1)`,
    [file('peer','group.webm')]);
  await as('family', 'update public.profiles set avatar=$1 where id=auth.uid()', [file('family','avatar.jpg')]);
  await as('pending', 'update public.profiles set avatar=$1 where id=auth.uid()', [file('pending','avatar.jpg')]);
  await as('staff', `insert into public.settings(key,value) values('staff',$1)`,
    [JSON.stringify([{n:'Técnico de prueba', f:file('staff','staff.jpg')}])]);
  for (const leaf of ['pending.jpg','private.webm','orphan.jpg']) {
    assert.equal(await visible('family',file('family',leaf)), true);
    assert.equal(await visible('peer',file('family',leaf)), false, leaf);
    assert.equal(await visible('staff',file('family',leaf)), true);
  }
  assert.equal(await visible('family',file('staff','reply.webm')), true);
  assert.equal(await visible('peer',file('staff','reply.webm')), false);
  const shared = [['family','approved.jpg'],['family','thumb.jpg'],['peer','group.webm'],
    ['family','child.jpg'],['family','avatar.jpg'],['staff','staff.jpg']];
  for (const [who, leaf] of shared) {
    assert.equal(await visible('peer',file(who,leaf)), true, leaf);
    assert.equal(await visible('pending',file(who,leaf)), false, leaf);
  }
  assert.equal(await visible('peer',file('pending','avatar.jpg')), false);
  assert.equal(await visible('pending',file('pending','avatar.jpg')), false,
    'ser propietario no da acceso antes de la aprobación');
  await db.exec('set role anon');
  await assert.rejects(db.query('select * from storage.objects'), /permission denied/);
  await db.exec('reset role');
  // Referencias inventadas en campos que una familia sí puede escribir.
  const secret = file('family','private.webm');
  await as('peer', 'update profiles set avatar=$1 where id=auth.uid()', [secret]);
  await as('peer', `insert into media(id,path,thumb,kind) values(203,$1,$1,'foto')`, [secret]);
  await as('peer', `insert into messages(channel,body,audio) values('grupo','Referencia inventada',$1)`, [secret]);
  assert.equal(await visible('peer',secret), false, 'una referencia inventada no revela archivos ajenos');

  // La edición de cualquier contenido publicado vuelve a la cola de moderación.
  await as('staff', `insert into matches(id,rival,fecha) values(501,'Rival de prueba','2026-11-23')`);
  for (const leaf of ['replacement.jpg','replacement-thumb.jpg']) {
    await db.query("insert into storage.objects(bucket_id,name,owner_id) values('media',$1,$2)",
      [file('family',leaf),ids.family]);
  }
  const edits = [
    ['path',file('family','replacement.jpg')],
    ['thumb',file('family','replacement-thumb.jpg')],
    ['kind','video'], ['caption','Comentario nuevo'], ['match_id',501], ['season','2027/28']
  ];
  for (const [column, value] of edits) {
    await as('staff','update media set approved=true where id=201');
    // Los nombres de columna proceden exclusivamente de la lista fija anterior.
    await as('family',`update media set ${column}=$1,approved=true where id=201`,[value]);
    assert.equal((await as('family','select approved from media where id=201')).rows[0].approved,false,column);
    assert.equal((await as('peer','select id from media where id=201')).rows.length,0,column);
    assert.equal(await visible('peer',file('family','replacement.jpg')),false,column);
  }
  await as('staff','update media set approved=true where id=201');
  assert.equal(await visible('peer',file('family','replacement.jpg')),true);
  // Guardar sin cambios no obliga a moderar otra vez; una edición del técnico tampoco.
  await as('family','update media set path=path,caption=caption where id=201');
  assert.equal((await as('peer','select approved from media where id=201')).rows[0].approved,true);
  await as('staff',"update media set caption='Revisado por técnico' where id=201");
  assert.equal((await as('peer','select approved from media where id=201')).rows[0].approved,true);
  console.log('OK: la sustitución de contenido requiere nueva aprobación');
  await as('staff', 'update profiles set approved=false where id=$1', [ids.family]);
  assert.equal(await visible('family',secret), false, 'la revocación también bloquea archivos propios');
  // El bucket también se comprueba aunque la ruta esté publicada.
  await db.exec("insert into storage.buckets(id,name) values('other','other')");
  await db.query("insert into storage.objects(bucket_id,name,owner_id) values('other',$1,$2)",
    [file('family','approved.jpg'),ids.family]);
  assert.equal((await as('staff', "select * from storage.objects where bucket_id='other'")).rows.length, 0);
  console.log('OK: RLS de archivos, audios privados, moderación, fotos compartidas y referencias inventadas');

  // Si desaparece el último técnico, el registro no se convierte en recuperación pública.
  await as('staff','update profiles set approved=false where id=auth.uid()');
  await as('pending','delete from profiles where id=auth.uid()');
  await as('pending',`insert into profiles(id,nombre,apellidos,role,approved,admin)
    values(auth.uid(),'Alta','Prueba','entrenador',true,true)`);
  assert.equal((await as('pending','select public.is_staff() as staff')).rows[0].staff,false);
  assert.equal((await as('pending','select approved from profiles where id=auth.uid()')).rows[0].approved,false);
  // La recuperación privada sigue funcionando y permite aprobar las altas posteriores.
  await db.query('update profiles set approved=true,admin=true where id=$1',[ids.staff]);
  await as('staff','update profiles set approved=true where id=$1',[ids.pending]);
  assert.equal((await as('pending','select public.is_staff() as staff')).rows[0].staff,true);
  console.log('OK: registro sin autoaprobación inicial ni al retirar el último técnico');
} finally {
  await db.close();
}

