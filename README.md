# San José · Estrellitas

App del equipo **Estrellitas** del Colegio San José: partidos en directo, estadísticas de cada jugador, entrenamientos y vídeos de los partidos. Se instala en el móvil desde el navegador (iPhone y Android), sin App Store.

- **Entrenador:** apunta los partidos en directo (goles, asistencias, paradas, cambios, tarjetas), valora a los jugadores, pasa lista en los entrenamientos, sube los enlaces de los vídeos y aprueba quién entra en la app.
- **Padres y jugadores:** ven el marcador en directo, las estadísticas del equipo, la ficha de su hijo (o la suya) y los vídeos.
- **Privacidad:** las valoraciones del entrenador y los datos de contacto de las familias solo los ve el entrenador. Nadie entra sin que el entrenador apruebe su alta. El número del DNI se comprueba pero **no se guarda**.

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

### 5. Darte de alta como entrenador
Abre la app, pulsa **Registrarse**, confirma el email y elige **Entrenador**. **El primer entrenador que se registra queda aprobado automáticamente.** Todos los demás (incluidos otros entrenadores) los apruebas tú desde **Perfil → Solicitudes de acceso**.

### 6. Invitar a los padres
Manda el enlace por el grupo de WhatsApp. Cada padre se registra, elige "Familiar de jugador" y a su hijo, y tú lo apruebas.

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
