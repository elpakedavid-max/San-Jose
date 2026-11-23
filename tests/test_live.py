"""Comprobación de la web publicada (GitHub Pages + Supabase real).
Solo lee: abre la pantalla de acceso, no inicia sesión ni escribe nada.
Se ejecuta con:  LIVE=1 pytest -q tests/test_live.py
"""
import os, pytest
from playwright.sync_api import sync_playwright

URL = os.environ.get('APP_URL', 'https://elpakedavid-max.github.io/San-Jose/')
pytestmark = pytest.mark.skipif(not os.environ.get('LIVE'), reason='solo con LIVE=1')


def test_web_publicada_carga_sin_errores():
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 390, 'height': 844})
        errs, bad = [], []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('response', lambda r: r.status >= 400 and 'github.io' in r.url and bad.append(f'{r.status} {r.url}'))
        pg.goto(URL, wait_until='networkidle')
        pg.wait_for_selector('#em', timeout=15000)
        assert pg.evaluate("!!(window.SJ_CONFIG&&window.SJ_CONFIG.supabaseUrl)"), 'config.js no cargó'
        b.close()
        assert not errs, f'Errores JavaScript en la web: {errs}'
        assert not bad, f'Ficheros que fallan: {bad}'
