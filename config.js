// Datos de conexión con Supabase (Project Settings → API).
// La clave "anon" / "publishable" es pública por diseño: la seguridad la dan
// las reglas de schema.sql. NUNCA pongas aquí la clave "service_role" / "secret".
//
// Si lo dejas vacío, la app funciona en MODO PRUEBA (los datos se guardan
// solo en el móvil donde se abre).
window.SJ_CONFIG = {
  supabaseUrl: 'https://ifhapipxopoosdmzddtx.supabase.co',
  supabaseKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlmaGFwaXB4b3Bvb3NkbXpkZHR4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTUzNDk4ODQsImV4cCI6MjExMDkyNTg4NH0.Yh5m-5JtmmyW7EBocM7ADO2E0o_G3z9qAlPlUSzXQm4'  // clave anon (pública)
};
