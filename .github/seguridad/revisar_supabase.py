#!/usr/bin/env python3
"""
Revisión de seguridad para apps con Supabase (MR Informática).

Comprueba:
  1. Que ninguna clave secreta de Supabase (service_role / sb_secret_) esté en el código.
  2. Que todas las tablas creadas en los .sql tengan Row Level Security activado.
  3. Políticas o permisos peligrosos: acceso para "anon"/"public" o "using (true)" en escrituras.
  4. Funciones "security definer" sin "set search_path" fijo.

Sale con código 1 si hay ERRORES (el flujo falla). Los AVISOS solo se muestran.
Uso: python3 revisar_supabase.py [carpeta]   (por defecto, la carpeta actual)
"""
import base64
import json
import os
import re
import sys

RAIZ = sys.argv[1] if len(sys.argv) > 1 else "."
CARPETAS_IGNORADAS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
EXTENSIONES_TEXTO = {".js", ".mjs", ".cjs", ".ts", ".json", ".html", ".py", ".sql", ".md",
                     ".yml", ".yaml", ".toml", ".env", ".txt", ".jsx", ".tsx", ".sh", ".ps1"}

errores, avisos = [], []


def ficheros():
    for carpeta, subcarpetas, nombres in os.walk(RAIZ):
        subcarpetas[:] = [d for d in subcarpetas if d not in CARPETAS_IGNORADAS]
        for n in nombres:
            ruta = os.path.join(carpeta, n)
            ext = os.path.splitext(n)[1].lower()
            if ext in EXTENSIONES_TEXTO or n.startswith(".env"):
                try:
                    if os.path.getsize(ruta) > 5_000_000:
                        continue
                    with open(ruta, encoding="utf-8", errors="ignore") as f:
                        yield os.path.relpath(ruta, RAIZ), f.read()
                except OSError:
                    pass


def linea(texto, pos):
    return texto.count("\n", 0, pos) + 1


def rol_jwt(token):
    try:
        carga = token.split(".")[1]
        carga += "=" * (-len(carga) % 4)
        return json.loads(base64.urlsafe_b64decode(carga)).get("role")
    except Exception:
        return None


RE_JWT = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")
RE_SECRETA = re.compile(r"sb_secret_[A-Za-z0-9_-]{10,}")

RE_TABLA = re.compile(r"create\s+table\s+(?:if\s+not\s+exists\s+)?([\w\".]+)", re.I)
RE_RLS = re.compile(r"alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?([\w\".]+)\s+enable\s+row\s+level\s+security", re.I)
RE_POLITICA = re.compile(r"create\s+policy\s+(.+?);", re.I | re.S)
RE_GRANT_ANON = re.compile(r"grant\s+([\w\s,]+?)\s+on\s+(?:table\s+)?([^;]+?)\s+to\s+([^;]*\b(?:anon|public)\b[^;]*);", re.I)
RE_DEFINER = re.compile(r"create\s+(?:or\s+replace\s+)?function\s+([\w\".]+).*?(?:\$\$|\$[a-z_]*\$)", re.I | re.S)


def normaliza(nombre):
    nombre = nombre.replace('"', "").lower()
    return nombre if "." in nombre else "public." + nombre


tablas, con_rls = {}, set()

for ruta, texto in ficheros():
    # 1. Claves secretas
    for m in RE_JWT.finditer(texto):
        if rol_jwt(m.group(0)) == "service_role":
            errores.append(f"{ruta}:{linea(texto, m.start())}: clave SERVICE_ROLE de Supabase en el código. "
                           "Quítala, cámbiala (rota) en Supabase y guárdala solo en variables de entorno del servidor.")
    for m in RE_SECRETA.finditer(texto):
        errores.append(f"{ruta}:{linea(texto, m.start())}: clave SECRETA de Supabase (sb_secret_) en el código. "
                       "Quítala y cámbiala (rota) en Supabase.")

    if not ruta.lower().endswith(".sql"):
        continue
    sql = re.sub(r"--[^\n]*", "", texto)  # quita comentarios de línea

    # 2. Tablas y RLS
    for m in RE_TABLA.finditer(sql):
        nombre = normaliza(m.group(1))
        if nombre.startswith("public.") or nombre.split(".")[0] not in ("auth", "storage"):
            tablas.setdefault(nombre, f"{ruta}:{linea(sql, m.start())}")
    for m in RE_RLS.finditer(sql):
        con_rls.add(normaliza(m.group(1)))
    # RLS activado en bucle dinámico (format('alter table ... %I enable row level security'))
    if re.search(r"%I\s+enable\s+row\s+level\s+security", sql, re.I):
        for lista in re.findall(r"array\s*\[([^\]]+)\]", sql, re.I):
            for t in re.findall(r"'([\w.]+)'", lista):
                con_rls.add(normaliza(t))

    # 3. Políticas peligrosas
    for m in RE_POLITICA.finditer(sql):
        p = " ".join(m.group(1).split()).lower()
        nombre_pol = p.split(" on ")[0]
        escritura = re.search(r"\bfor\s+(insert|update|delete|all)\b", p) or not re.search(r"\bfor\s+select\b", p)
        para_anon = re.search(r"\bto\s+[^()]*\b(anon|public)\b", p)
        abierta = re.search(r"(using|with\s+check)\s*\(\s*true\s*\)", p)
        donde = f"{ruta}:{linea(sql, m.start())}"
        if escritura and abierta and (para_anon or " to " not in p):
            errores.append(f"{donde}: la política {nombre_pol} permite ESCRIBIR a cualquiera (true) sin iniciar sesión.")
        elif escritura and para_anon:
            avisos.append(f"{donde}: la política {nombre_pol} permite escribir a usuarios anónimos. Revisa que sea intencionado.")
        elif abierta and (para_anon or " to " not in p):
            avisos.append(f"{donde}: la política {nombre_pol} deja LEER a cualquiera (using true). Revisa que esos datos sean públicos.")

    for m in RE_GRANT_ANON.finditer(sql):
        permisos = m.group(1).lower()
        if "execute" in permisos and "function" in m.group(2).lower():
            avisos.append(f"{ruta}:{linea(sql, m.start())}: se da permiso de ejecutar funciones a anon/public. Revisa que sea intencionado.")
        elif re.search(r"insert|update|delete|all|truncate", permisos):
            avisos.append(f"{ruta}:{linea(sql, m.start())}: GRANT de escritura a anon/public ({permisos.strip()}). "
                          "Con RLS bien puesto no es grave, pero mejor darlo solo a 'authenticated'.")

    # 4. security definer sin search_path
    for m in RE_DEFINER.finditer(sql):
        cabecera = m.group(0).lower()
        if "security definer" in cabecera and "search_path" not in cabecera:
            avisos.append(f"{ruta}:{linea(sql, m.start())}: la función {m.group(1)} es SECURITY DEFINER sin "
                          "'set search_path = public'. Añádelo para evitar que se suplanten tablas o funciones.")

for nombre, donde in sorted(tablas.items()):
    if nombre not in con_rls:
        errores.append(f"{donde}: la tabla {nombre} NO tiene Row Level Security activado "
                       f"(añade: alter table {nombre} enable row level security;). Sin RLS, cualquiera con la clave anon puede leerla y modificarla.")

# Informe
resumen = os.environ.get("GITHUB_STEP_SUMMARY")
lineas = ["## Revisión de Supabase", ""]
lineas.append(f"Tablas encontradas: {len(tablas)} · con RLS: {len([t for t in tablas if t in con_rls])}")
lineas.append("")
if errores:
    lineas += ["### ❌ Errores (hay que corregirlos)", ""] + [f"- {e}" for e in errores] + [""]
if avisos:
    lineas += ["### ⚠️ Avisos (revisar)", ""] + [f"- {a}" for a in avisos] + [""]
if not errores and not avisos:
    lineas.append("✅ Todo correcto.")
texto = "\n".join(lineas)
print(texto)
if resumen:
    with open(resumen, "a", encoding="utf-8") as f:
        f.write(texto + "\n")
sys.exit(1 if errores else 0)
