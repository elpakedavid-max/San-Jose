"""Smoke de solo lectura. EXPECTED_SHA impide validar una release anterior."""
import hashlib
import os
import re
import time
import pytest
from playwright.sync_api import sync_playwright

URL = os.environ.get('APP_URL', 'https://elpakedavid-max.github.io/San-Jose/')
pytestmark = pytest.mark.skipif(not os.environ.get('LIVE'), reason='solo con LIVE=1')


def wait_release(url, expected, request, pause=time.sleep, attempts=40):
    for attempt in range(attempts):
        try:
            response = request(url.rstrip('/') + f'/release.json?expected={expected}&attempt={attempt}',
                               headers={'Cache-Control': 'no-cache'}, timeout=5000)
            if response.status == 200:
                manifest = response.json()
                if manifest.get('sha') == expected and manifest.get('assets'):
                    return manifest
        except Exception:
            pass  # Un 404 temporal o un fallo de red no valida la release anterior.
        if attempt + 1 < attempts:
            pause(3)
    raise AssertionError('Pages no sirve la revisión esperada; no se valida la release anterior')


def test_web_publicada_carga_sin_errores():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 390, 'height': 844}, service_workers='block')
        errors, bad = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('response', lambda r: r.status >= 400 and 'github.io' in r.url and bad.append(r.status))
        expected = os.environ.get('EXPECTED_SHA')
        try:
            if expected:
                assert re.fullmatch(r'[0-9a-f]{40}', expected)
                manifest = wait_release(URL, expected, page.request.get)
                for name, digest in manifest['assets'].items():
                    assert re.fullmatch(r'[\w./-]+', name) and '..' not in name
                    response = page.request.get(URL.rstrip('/') + '/' + name + '?release=' + expected,
                                                headers={'Cache-Control': 'no-cache'}, timeout=15000)
                    assert response.status == 200, f'Recurso no disponible: {name}'
                    assert hashlib.sha256(response.body()).hexdigest() == digest, f'Recurso de otra release: {name}'
            page.goto(URL + ('?release=' + expected if expected else ''), wait_until='networkidle')
            page.wait_for_selector('#em', timeout=15000)
            assert page.evaluate("!!(window.SJ_CONFIG?.supabaseUrl && window.SJ_CONFIG?.supabaseKey && window.supabase?.createClient)"), 'Configuración o SDK ausente: no se acepta modo prueba como smoke remoto'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Desbordamiento horizontal'
            assert not errors, 'Errores JavaScript en la pantalla de acceso'
            assert not bad, 'Recursos de Pages con error HTTP'
        finally:
            browser.close()
