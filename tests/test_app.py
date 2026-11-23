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


def login_coach(pg, approved=True):
    pg.fill('#em', 'coach@x.es'); pg.fill('#pw', '12345678'); pg.click('[data-act=login]'); pg.wait_for_timeout(300)
    pg.click('[data-act=role][data-v=entrenador]'); pg.click('[data-act=go][data-v=reg]')
    pg.fill('#f-n', 'D'); pg.fill('#f-a', 'X'); pg.click('[data-act=next]')
    pg.fill('#f-t', '600000000'); pg.click('[data-act=next]'); pg.click('[data-act=next]')
    pg.check('#c1'); pg.click('[data-act=next]'); pg.wait_for_timeout(300)
    if approved:
        # Alta del primer administrador desde el panel privado, no desde el registro.
        pg.evaluate("()=>{Object.assign(window.__DB.profiles.find(x=>x.id==='coach'),{approved:true,admin:true});window.__fire()}")
        pg.wait_for_timeout(500)


def add_match(pg, ev):
    pg.evaluate("ev=>{window.__DB.matches.push({id:7,season:'2026/27',rival:'Marbella',fecha:'2026-11-14',local:true,dur:50,estado:'fin',tit:[5,6],ev,acc:0,run:null,video:null});window.__fire()}", ev)
    pg.wait_for_timeout(500)


def test_pantalla_de_acceso(app):
    assert app.locator('#em').is_visible()
    assert app.locator('[data-act=login]').is_visible()


def test_primer_entrenador_espera_aprobacion(app):
    login_coach(app, approved=False)
    assert app.get_by_text('⏳ Pendiente de aprobación', exact=True).is_visible()
    assert app.evaluate("window.__DB.profiles[0].approved") is False
    assert app.locator('[data-act=tab]').count() == 0


def test_eliminar_perfil_explica_datos_conservados(app):
    login_familia(app)
    app.click('[data-act=tab][data-v=perfil]')
    card = app.locator('#profile-removal')
    assert 'cuenta de inicio de sesión, mensajes, fotos, vídeos y registro de actividad' in card.inner_text()
    assert 'borrado completo' in card.inner_text()
    assert app.get_by_text('Borrar mis datos', exact=True).count() == 0
    card.locator('[data-act=delme]').click()
    assert app.evaluate("window.__DB.profiles.some(p=>p.id==='fam')")
    assert card.get_by_role('button', name='Pulsa otra vez para eliminar solo tu perfil').is_visible()
    card.locator('[data-act=delme]').click()
    app.wait_for_timeout(300)
    assert not app.evaluate("window.__DB.profiles.some(p=>p.id==='fam')")
    assert app.locator('#em').is_visible()


def test_eliminar_perfil_ingles(app):
    login_familia(app)
    app.click('[data-act=tab][data-v=perfil]')
    app.click('[data-act=lang][data-v=en]')
    card = app.locator('#profile-removal')
    assert card.get_by_role('button', name='Remove my profile', exact=True).is_visible()
    assert 'messages, photos, videos and activity log remain' in card.inner_text()
    card.locator('[data-act=delme]').click()
    assert card.get_by_role('button', name='Tap again to remove only your profile').is_visible()


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


def test_gol_en_propia_no_permite_atribuir_jugador_ni_asistencia(app):
    login_coach(app)
    add_match(app, [{"t": "gol", "min": 10, "pl": None, "asis": 0, "tipo": "propia"}])
    app.click('[data-act=tab][data-v=partidos]')
    app.click('[data-act=match]')
    app.click('[data-act=medit]')

    assert app.get_by_text('Gol en propia puerta del rival', exact=False).is_visible()
    assert app.locator('[data-chg=evpl][data-v="0"]').count() == 0
    assert app.locator('[data-chg=evas][data-v="0"]').count() == 0

    app.select_option('[data-chg=evty][data-v="0"]', 'jugada')
    scorer = app.locator('[data-chg=evpl][data-v="0"]')
    assert scorer.input_value() == '0'
    scorer.select_option('5')
    assert app.evaluate('window.__DB.matches[0].ev[0].pl') == 5
    app.select_option('[data-chg=evas][data-v="0"]', '6')

    app.select_option('[data-chg=evty][data-v="0"]', 'propia')
    event = app.evaluate('window.__DB.matches[0].ev[0]')
    assert event['pl'] is None and event['asis'] == 0


def login_familia(pg, pid=5):
    pg.evaluate("pid=>window.__DB.profiles.push({id:'fam',approved:true,role:'familiar',pid,nombre:'Ana',apellidos:'Prueba',email:'fam@x.es',admin:false})", pid)
    pg.fill('#em', 'fam@x.es'); pg.fill('#pw', '12345678'); pg.click('[data-act=login]'); pg.wait_for_timeout(500)


def test_familia_pone_foto_de_su_hijo(app, tmp_path):
    login_familia(app)
    img = tmp_path / 'f.png'
    app.evaluate("""async()=>{const c=document.createElement('canvas');c.width=c.height=40;c.getContext('2d').fillRect(0,0,40,40);window.__png=c.toDataURL('image/png')}""")
    import base64
    img.write_bytes(base64.b64decode(app.evaluate("window.__png").split(',')[1]))
    app.click('[data-act=tab][data-v=perfil]') if app.locator('[data-act=tab][data-v=perfil]').count() else None
    app.click('button.av'); app.wait_for_timeout(200)
    assert 'Foto de Tadeo' in app.inner_text('body')
    app.set_input_files('#kphf', str(img)); app.wait_for_timeout(800)
    photo = app.evaluate("window.__DB.players.find(x=>x.id==5).photo")
    assert photo and photo.startswith('fam/child_5_')
    # no puede cambiar la de otro jugador
    r = app.evaluate("async()=>{const r=await window.supabase.createClient().rpc('set_child_photo',{p_player:6,p_path:'fam/x.jpg'});return !!r.error}")
    assert r
    app.click('[data-act=kphdel]'); app.wait_for_timeout(300)
    assert app.evaluate("window.__DB.players.find(x=>x.id==5).photo") is None


def test_idioma_ingles(app):
    login_coach(app)
    add_match(app, [{"t": "gol", "min": 3, "pl": 5, "asis": 6, "tipo": "cabeza"}])
    app.click('[data-act=tab][data-v=perfil]'); app.wait_for_timeout(150)
    app.click('[data-act=lang][data-v=en]'); app.wait_for_timeout(200)
    assert 'My profile' in app.inner_text('body')
    app.click('[data-act=tab][data-v=stats]'); app.wait_for_timeout(200)
    txt = app.inner_text('body')
    assert 'How we score' in txt and 'Header' in txt and 'Estadísticas' not in txt
    app.click('[data-act=tab][data-v=chat]'); app.wait_for_timeout(200)
    app.fill('#mtxt', 'Gol de cabeza'); app.click('[data-act=msend]'); app.wait_for_timeout(300)
    assert 'Gol de cabeza' in app.inner_text('#msgs')  # los mensajes no se traducen
    app.click('[data-act=tab][data-v=perfil]'); app.click('[data-act=lang][data-v=es]'); app.wait_for_timeout(200)
    assert 'Mi perfil' in app.inner_text('body')


def test_guia_de_registro(app):
    app.click('[data-act=help]'); app.wait_for_timeout(200)
    assert app.locator('img[src="guia/es-1.jpg"]').count() == 1
    app.click('.pad [data-act=go]'); app.wait_for_timeout(150)
    assert app.locator('#em').is_visible()
    app.click('[data-act=lang][data-v=en]'); app.click('[data-act=help]'); app.wait_for_timeout(200)
    assert app.locator('img[src="guia/en-3.jpg"]').count() == 1
    assert 'How to sign up' in app.inner_text('body')

