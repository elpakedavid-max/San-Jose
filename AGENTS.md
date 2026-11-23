# Instrucciones para agentes (Codex, Claude Code, etc.)

App web (PWA) del equipo de fútbol infantil **San José · Estrellitas**.
Publicada en https://elpakedavid-max.github.io/San-Jose/ (GitHub Pages, rama `main`).
Responde y escribe los mensajes de commit **en español**.

## Estructura
- `index.html` — toda la app (HTML + CSS + un único `<script>` sin framework ni build).
  - Estado global `S`, escrituras vía `W`, acciones con `data-act` (objeto `ACT`) y cambios con `data-chg` (objeto `CHG`), pintado con `render()`.
- `config.js` — URL y clave pública (anon) de Supabase + clave de app de Dropbox. Se carga como `config.js?v=N`: si lo cambias, sube N.
- `sw.js` — service worker. **En cada cambio publicado sube `const CACHE = 'sanjose-vNN'`** o los móviles verán la versión vieja. No debe interceptar peticiones Range/vídeo/audio.
- `schema.sql` — esquema de Supabase (tablas, RLS, funciones). Mantenlo sincronizado con cualquier cambio de base de datos.
- `tests/` — pruebas con Playwright y un Supabase simulado (`mock_supabase.js`).

## Cómo verificar
```bash
pip install pytest playwright && playwright install chromium
pytest -q tests/test_app.py          # no toca datos reales
LIVE=1 pytest -q tests/test_live.py  # solo lee la web publicada
```
Antes de dar algo por terminado: pruebas en verde, sin errores de JavaScript en consola y, si añades una función, añade su prueba en `tests/test_app.py`.
GitHub Actions (`.github/workflows/pruebas.yml`) las ejecuta en cada push, en cada PR y cada mañana.

## Reglas
- **Datos de menores**: nunca metas nombres, fotos, vídeos ni datos reales de jugadores o familias en el código, las pruebas, los issues o los logs. Usa datos inventados.
- **Nunca** pongas en el repo claves secretas (`service_role`, contraseñas, tokens). Solo la clave pública anon de Supabase puede estar en `config.js`.
- No cambies la seguridad (RLS, funciones `is_staff`, `is_member`, `profiles_guard`…) sin explicarlo en el PR.
- No ejecutes SQL ni migraciones contra la base de datos real; propón el cambio en `schema.sql` y en el PR.
- Cambios pequeños y en una rama con PR; no hagas push directo a `main` salvo que el dueño lo pida.
- Mantén la app en un solo fichero, sin dependencias nuevas ni paso de compilación, y en español.
- Diseño pensado para móvil (iPhone): prueba con viewport 390×844.

## Pautas de revisión de código (para revisiones automáticas de PR)
Marca como problema grave:
- Cualquier dato real de menores, clave secreta o token añadido al repo.
- Cambios que relajen la seguridad de Supabase (RLS, `is_staff`, `is_member`, `profiles_guard`, `media_guard`, `messages_guard`) o que dejen ver datos a usuarios no aprobados.
- Cambios publicados en `index.html` sin subir `CACHE` en `sw.js`.
- Que `sw.js` pase a interceptar peticiones de vídeo/audio o con cabecera Range (rompe los vídeos en iPhone).
- Errores de JavaScript, pruebas en rojo o funciones nuevas sin prueba.
- Textos de la app que no estén en español o que no se vean bien en un móvil de 390 px.
