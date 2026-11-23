"""Pruebas automáticas de la app San José · Estrellitas.

Abren index.html en un Chromium sin cabeza con un Supabase simulado
(tests/mock_supabase.js), así que NO tocan la base de datos real.
Ejecutar:  pip install pytest playwright && playwright install chromium && pytest -q tests
"""
import json, pathlib, pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
MOCK = str(ROOT / 'tests' / 'mock_supabase.js')
CFG = "window.SJ_CONFIG={supabaseUrl:'https://x.supabase.co',supabaseKey:'k'}"


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def app(browser):
    pg = browser.new_page(viewport={'width': 390, 'height': 844})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.route('**/fonts.*/**', lambda r: r.abort())
    pg.route('**/supabase.js', lambda r: r.fulfill(path=MOCK, content_type='text/javascript'))
    pg.route('**/config.js*', lambda r: r.fulfill(body=CFG, content_type='text/javascript'))
    pg.goto((ROOT / 'index.html').as_uri())
    pg.wait_for_timeout(300)
    pg.errs = errs
    yield pg
    assert not errs, f'Errores JavaScript: {errs}'
    pg.close()


def login_coach(pg):
    pg.fill('#em', 'coach@x.es'); pg.fill('#pw', '12345678'); pg.click('[data-act=login]'); pg.wait_for_timeout(300)
    pg.click('[data-act=role][data-v=entrenador]'); pg.click('[data-act=go][data-v=reg]')
    pg.fill('#f-n', 'D'); pg.fill('#f-a', 'X'); pg.click('[data-act=next]')
    pg.fill('#f-t', '600000000'); pg.click('[data-act=next]'); pg.click('[data-act=next]')
    pg.check('#c1'); pg.click('[data-act=next]'); pg.wait_for_timeout(300)


def add_match(pg, ev):
    pg.evaluate("ev=>{window.__DB.matches.push({id:7,season:'2026/27',rival:'Marbella',fecha:'2026-11-14',local:true,dur:50,estado:'fin',tit:[5,6],ev,acc:0,run:null,video:null});window.__fire()}", ev)
    pg.wait_for_timeout(500)


def test_pantalla_de_acceso(app):
    assert app.locator('#em').is_visible()
    assert app.locator('[data-act=login]').is_visible()


def test_todas_las_pestanas_cargan(app):
    login_coach(app)
    add_match(app, [{"t": "gol", "min": 10, "pl": 5, "asis": 6}])
    for t in ['inicio', 'partidos', 'chat', 'galeria', 'plantilla', 'stats']:
        app.click(f'[data-act=tab][data-v={t}]'); app.wait_for_timeout(150)
        assert app.locator('main, #app').first.inner_text().strip(), f'Pestaña vacía: {t}'


def test_tipo_de_gol_y_propia_puerta(app):
    login_coach(app)
    add_match(app, [{"t": "gol", "min": None, "pl": 5, "asis": 0}])
    app.click('[data-act=tab][data-v=partidos]'); app.click('[data-act=match]'); app.click('[data-act=medit]')
    app.select_option('[data-chg=evty][data-v="0"]', 'penalti'); app.wait_for_timeout(150)
    app.select_option('#egt', 'propia'); app.click('[data-act=evadd]'); app.wait_for_timeout(150)
    ev = json.loads(app.evaluate("JSON.stringify(window.__DB.matches[0].ev)"))
    assert ev[0]['tipo'] == 'penalti'
    assert ev[1]['tipo'] == 'propia' and ev[1]['pl'] is None


def test_goles_en_estadisticas(app):
    login_coach(app)
    add_match(app, [{"t": "gol", "min": 3, "pl": 5, "asis": 6, "tipo": "cabeza"}, {"t": "gol", "min": 9, "pl": None, "tipo": "propia"}])
    app.click('[data-act=tab][data-v=stats]'); app.wait_for_timeout(200)
    txt = app.inner_text('body')
    assert 'Cómo marcamos' in txt and 'De cabeza' in txt


def test_varias_posiciones(app):
    login_coach(app)
    app.click('[data-act=tab][data-v=plantilla]'); app.click('[data-act=player][data-v="6"]'); app.click('[data-act=pedit]')
    app.click('[data-act=postog][data-v="Extremo derecho"]'); app.click('[data-act=psave]'); app.wait_for_timeout(150)
    dem = app.evaluate("window.__DB.players.find(x=>x.id==6).dem")
    assert 'Delantero' in dem and 'Extremo derecho' in dem


def test_chat_envia_mensaje(app):
    login_coach(app)
    app.click('[data-act=tab][data-v=chat]'); app.wait_for_timeout(200)
    app.fill('#mtxt', 'Hola equipo'); app.click('[data-act=msend]'); app.wait_for_timeout(200)
    assert app.evaluate("window.__DB.messages.some(m=>m.text==='Hola equipo'||m.body==='Hola equipo'||JSON.stringify(m).includes('Hola equipo'))")
