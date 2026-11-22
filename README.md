# San José · Estrellitas

App del equipo **Estrellitas** del Colegio San José: partidos en directo, estadísticas de cada jugador, entrenamientos y vídeos de los partidos. Se instala en el móvil desde el navegador (iPhone y Android), sin App Store.

- **Administrador y entrenador:** validan las altas (y vinculan a cada familia con su hijo), apuntan los partidos en directo, valoran a los jugadores, pasan lista, publican vídeos y fotos, y aprueban lo que suben las familias.
- **Familias:** ven el marcador en directo, las estadísticas del equipo, la ficha de su hijo y los partidos grabados, y pueden subir fotos y vídeos cortos (se publican cuando un administrador los aprueba).
- **Privacidad:** el registro no pide DNI. Las valoraciones y los datos de contacto solo los ven los administradores. Nadie entra sin que un administrador valide su alta. Fotos y vídeos se guardan en un almacenamiento privado: solo los ven los miembros aprobados.

**Límites del plan gratis de Supabase:** 1 GB de almacenamiento, archivos de hasta 50 MB y 5 GB de descargas al mes. Las fotos se reducen automáticamente antes de subirlas. Los partidos completos se comparten con un enlace (iCloud, Drive…) desde la ficha del partido.

Sin configurar nada, la app funciona en **modo prueba**: los datos se guardan solo en el móvil donde se abre.

---

## Puesta en marcha (una sola vez, unos 15 minutos)

### 1. Crear la base de datos en Supabase (gratis)
1. Entra en <https://supabase.com>, crea una cuenta y pulsa **New project**. Ponle de nombre `sanjose`, elige la región **Europe (Frankfurt o Paris)** y una contraseña de base de datos (guárdala).
2. Cuando termine de crearse, ve a **SQL Editor → New query**, pega todo el contenido de [`schema.sql`](schema.sql) y pulsa **Run**. Esto crea las tablas, los permisos y la plantilla de los Estrellitas.
3. Ve a **Project Settings → API** y copia:
   - **Project URL** (algo como `https://abcd1234.supabase.co`)
   - La clave **anon public** (o **publishable**)

### 2. Conectar la app
Edita [`config.js`](config.js) en GitHub (icono del lápiz) y pega los dos valores:

```js
window.SJ_CONFIG = {
  supabaseUrl: 'https://abcd1234.supabase.co',
  supabaseKey: 'eyJhbGciOi...'
};
```

> La clave *anon/publishable* es pública por diseño. **Nunca** pongas la clave *service_role/secret*.

### 3. Publicar la web (GitHub Pages)
En el repositorio: **Settings → Pages → Source: Deploy from a branch → Branch: `main` / `(root)` → Save**.
Al minuto la app estará en **https://elpakedavid-max.github.io/San-Jose/**

### 4. Ajustes de acceso en Supabase
En **Authentication → URL Configuration**:
- **Site URL:** `https://elpakedavid-max.github.io/San-Jose/`
- **Redirect URLs:** añade la misma dirección.

Así los enlaces de "confirmar email" y "recuperar contraseña" vuelven a la app.

### 5. Administradores
Todo se gestiona en **Perfil → ⚙️ Administración**: solicitudes de acceso, usuarios (rol, cargo, jugador vinculado, dar o quitar administrador, quitar acceso), cuerpo técnico, plantilla y partidos (crear, editar datos y goles).

Si no hay ningún administrador, el primer **entrenador** que se registra queda aprobado automáticamente. Cualquier miembro aprobado puede pasar a ser administrador desde **Perfil → Miembros del equipo → Hacer administrador**. Las solicitudes se validan en **Perfil → Solicitudes de acceso**, eligiendo a qué jugador se vincula cada familia.

### 6. Invitar a los padres
Manda el enlace por el grupo de WhatsApp. Cada padre se registra, elige "Familiar de jugador" y escribe el nombre de su hijo; el administrador lo valida.

**Instalarla en el iPhone:** abrir el enlace en **Safari → botón Compartir → Añadir a pantalla de inicio**.
**En Android:** Chrome → menú ⋮ → **Instalar app** / **Añadir a pantalla de inicio**.

---

## Opcional
- **Entrar con Google o Apple:** se activa en Supabase → Authentication → Providers. Hasta entonces los botones avisan de que se use email y contraseña.
- **Correos de confirmación:** Supabase manda unos pocos correos por hora con su servidor de prueba. Si se registran muchos padres a la vez, configura un SMTP propio (Authentication → Emails → SMTP), por ejemplo el de Microsoft 365 o Brevo.
- **Dominio propio** (p. ej. `sanjose.mrinformaticamarbella.com`): Settings → Pages → Custom domain y un registro CNAME a `elpakedavid-max.github.io`. Después actualiza las URL del paso 4.

## Pendiente antes de abrirla a las familias
- **Política de privacidad del club:** el registro pide aceptarla. Hay que enlazar la política real del colegio o redactarla con el responsable de protección de datos.
- **Permisos de imagen:** la app guarda si cada familia acepta fotos y vídeos. Comprueba esa casilla antes de compartir grabaciones de los partidos.

## Archivos
| Archivo | Qué es |
|---|---|
| `index.html` | La app completa |
| `config.js` | Conexión con Supabase |
| `schema.sql` | Tablas, permisos y plantilla inicial |
| `sw.js`, `manifest.webmanifest`, `icon-*.png` | Para que se instale como app y abra rápido |
