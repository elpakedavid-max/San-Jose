// Datos de conexión con Supabase (Project Settings → API).
// La clave "anon" / "publishable" es pública por diseño: la seguridad la dan
// las reglas de schema.sql. NUNCA pongas aquí la clave "service_role" / "secret".
//
// Si lo dejas vacío, la app funciona en MODO PRUEBA (los datos se guardan
// solo en el móvil donde se abre).
window.SJ_CONFIG = {
  supabaseUrl: '',   // p. ej. 'https://abcdefghijkl.supabase.co'
  supabaseKey: ''    // clave anon / publishable
};
