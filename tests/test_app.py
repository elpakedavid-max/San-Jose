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
    # El cierre remoto se simula; ninguna prueba llama al Auth real.
    pg.route('**/auth/v1/logout*', lambda r: r.fulfill(status=503, body='sin red'))
    # Los vídeos de YouTube incrustados no se cargan en las pruebas.
    pg.route('**/*youtube*.com/**', lambda r: r.fulfill(body='<!doctype html><title>video</title>', content_type='text/html'))
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


def test_logout_sin_red_no_recupera_sesion_al_recargar(app):
    login_coach(app)
    assert app.evaluate("!!localStorage.getItem('sb-x-auth-token')")
    app.click('[data-act=tab][data-v=perfil]')
    app.click('[data-act=logout]')
    app.wait_for_selector('#em')
    assert app.evaluate("localStorage.getItem('sb-x-auth-token')") is None
    app.reload()
    app.wait_for_selector('#em')
    assert app.locator('[data-act=tab]').count() == 0


@pytest.mark.parametrize('editor', [False, True])
def test_revocacion_bloquea_chat_y_editor(app, editor):
    login_coach(app)
    if editor:
        add_match(app, [])
        app.click('[data-act=tab][data-v=partidos]')
        app.click('[data-act=match]'); app.click('[data-act=medit]')
        app.locator('#er').focus()
    else:
        app.click('[data-act=tab][data-v=chat]')
        app.fill('#mtxt', 'Borrador sintético privado')
        app.locator('#mtxt').focus()
    app.evaluate("()=>{window.__DB.profiles.find(p=>p.id==='coach').approved=false;window.__fire()}")
    app.get_by_text('⏳ Pendiente de aprobación', exact=True).wait_for()
    assert app.locator('#mtxt, #er, [data-act=tab], [data-act=msave]').count() == 0


def test_cambio_de_cuenta_no_conserva_panel_tecnico(app):
    login_coach(app)
    app.click('[data-act=tab][data-v=perfil]')
    app.click('[data-act=logout]')
    app.wait_for_selector('#em')
    login_familia(app)
    app.click('[data-act=tab][data-v=perfil]')
    assert app.locator('[data-act=go][data-v=admin]').count() == 0


def test_retirar_permisos_tecnicos_cierra_editor(app):
    login_coach(app)
    add_match(app, [])
    app.click('[data-act=tab][data-v=partidos]')
    app.click('[data-act=match]'); app.click('[data-act=medit]')
    app.locator('#er').focus()
    app.evaluate("()=>{Object.assign(window.__DB.profiles.find(p=>p.id==='coach'),{role:'familiar',admin:false});window.__fire()}")
    app.locator('[data-act=tab][data-v=perfil]').wait_for()
    assert app.locator('#er, [data-act=msave]').count() == 0
    app.click('[data-act=tab][data-v=perfil]')
    assert app.locator('[data-act=go][data-v=admin]').count() == 0


def test_reconfirmar_sesion_conserva_formulario_de_registro(app):
    app.fill('#em', 'alta@x.es'); app.fill('#pw', '12345678'); app.click('[data-act=login]')
    app.locator('[data-act=role][data-v=familiar]').wait_for()
    app.click('[data-act=role][data-v=familiar]'); app.click('[data-act=go][data-v=reg]')
    app.fill('#f-n', 'Prueba'); app.fill('#f-a', 'Registro'); app.click('[data-act=next]')
    app.fill('#f-t', '600000000')
    app.evaluate("window.__login('alta')")
    app.wait_for_timeout(300)
    assert app.locator('#f-t').input_value() == '600000000'
    app.click('[data-act=next]')
    assert app.locator('#f-h').is_visible()


def test_error_inicial_de_acceso_ofrece_reintento(app):
    app.evaluate("()=>{window.__profileError=true;window.__DB.profiles.push({id:'fam',approved:true,role:'familiar',nombre:'Prueba',apellidos:'Acceso'})}")
    app.fill('#em', 'fam@x.es'); app.fill('#pw', '12345678'); app.click('[data-act=login]')
    app.locator('[data-act=recheck]').wait_for()
    assert app.locator('[data-act=tab]').count() == 0
    app.evaluate('window.__profileError=false')
    app.click('[data-act=recheck]')
    app.locator('[data-act=tab][data-v=perfil]').wait_for()


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


def test_mejor_jugada_y_paradas(app):
    login_coach(app)
    add_match(app, [{"t": "parada", "min": 4, "pl": 5}])
    app.evaluate("()=>{window.__DB.matches[0].video=JSON.stringify([{t:'Primera parte',u:'https://x/v.mp4'}]);window.__fire()}")
    app.wait_for_timeout(300)
    app.click('[data-act=tab][data-v=partidos]'); app.click('[data-act=match]'); app.click('[data-act=medit]')
    app.select_option('#et', 'top'); app.wait_for_timeout(150)
    app.select_option('#ep', '6'); app.fill('#edesc', 'Regate y pase')
    app.click('[data-act=evadd]'); app.wait_for_timeout(150)
    ev = app.evaluate("window.__DB.matches[0].ev[1]")
    assert ev['t'] == 'top' and ev['pl'] == 6 and ev['desc'] == 'Regate y pase'
    assert app.locator('[data-act=clip], [data-act=clipmark], button:has-text("Marcar")').count() >= 1


def test_mejores_jugadas_en_estadisticas(app):
    login_coach(app)
    add_match(app, [{"t": "parada", "min": 4, "pl": 5}, {"t": "top", "min": 8, "pl": 6, "desc": "Regate"}])
    app.click('[data-act=tab][data-v=stats]'); app.wait_for_timeout(200)
    txt = app.inner_text('body')
    assert 'Mejores jugadas y paradas (2)' in txt and 'Regate' in txt



def test_galeria_no_descarga_videos(app):
    login_coach(app)
    app.evaluate("""()=>{const D=window.__DB;D.media=D.media||[];D.media.push(
      {id:501,path:'coach/a.mp4',thumb:null,kind:'video',approved:true,season:'2026/27',uploader:'coach',created_at:new Date().toISOString()},
      {id:502,path:'coach/b.mp4',thumb:'coach/b_t.jpg',kind:'video',approved:true,season:'2026/27',uploader:'coach',created_at:new Date().toISOString()},
      {id:503,path:'coach/c.jpg',thumb:'coach/c_t.jpg',kind:'foto',approved:true,season:'2026/27',uploader:'coach',created_at:new Date().toISOString()});window.__fire()}""")
    app.click('[data-act=tab][data-v=galeria]'); app.wait_for_timeout(500)
    assert app.locator('.tile video').count() == 0
    assert app.locator('.tile .vph').count() >= 1
    assert app.evaluate("localStorage.getItem('sj-urlc')") is not None


def test_privado_entre_familias(app):
    app.evaluate("()=>{window.__DB.profiles.push({id:'peer',approved:true,role:'familiar',pid:6,nombre:'Luis',apellidos:'Prueba',email:'peer@x.es'})}")
    login_familia(app)
    app.click('[data-act=tab][data-v=chat]'); app.wait_for_timeout(200)
    app.click('[data-act=chsel][data-v=dms]'); app.wait_for_timeout(200)
    app.select_option('#dmto', 'peer'); app.click('[data-act=dmnew]'); app.wait_for_timeout(200)
    app.fill('#mtxt', 'Hola Luis'); app.click('[data-act=msend]'); app.wait_for_timeout(300)
    ch = app.evaluate("window.__DB.messages.find(m=>m.body==='Hola Luis')?.channel")
    assert ch == 'dm:' + ':'.join(sorted(['fam', 'peer']))
    assert 'Solo la leéis vosotros dos' in app.inner_text('body')


def test_estadisticas_en_directo(app):
    login_coach(app)
    app.evaluate("()=>{window.__DB.matches.push({id:9,season:'2026/27',rival:'Rival Prueba',fecha:'2026-11-29',local:true,dur:50,estado:'live',tit:[5,6],ev:[{t:'gol',min:3,pl:5}],acc:120,run:null,video:null});window.__fire()}")
    app.wait_for_timeout(400)
    app.click('[data-act=tab][data-v=partidos]'); app.click('[data-act=match][data-v="9"]'); app.wait_for_timeout(200)
    app.click('[data-act=golive]'); app.wait_for_timeout(200)
    app.click('[data-act=st][data-v="corner:n"]'); app.click('[data-act=st][data-v="corner:n"]')
    app.click('[data-act=st][data-v="corner:r"]'); app.click('[data-act=st][data-v="tiro_f:r"]')
    app.click('[data-act=stm][data-v="corner:n"]'); app.wait_for_timeout(200)
    ev = app.evaluate("window.__DB.matches.find(m=>m.id==9).ev.filter(e=>e.t==='st').map(e=>e.k+':'+e.s)")
    assert sorted(ev) == ['corner:n', 'corner:r', 'tiro_f:r']
    assert app.inner_text('[data-act=st][data-v="tiro_p:n"]') == '1'  # el gol cuenta como tiro a puerta
    app.click('[data-act=undo]'); app.wait_for_timeout(150)  # deshacer quita el gol, no las estadísticas
    ev = app.evaluate("window.__DB.matches.find(m=>m.id==9).ev.map(e=>e.t)")
    assert 'gol' not in ev and ev.count('st') == 3
    app.fill('#strm', 'https://youtube.com/live/abcdefghijk'); app.click('[data-act=strsave]'); app.wait_for_timeout(200)
    assert app.evaluate("window.__DB.matches.find(m=>m.id==9).stream") == 'https://youtube.com/live/abcdefghijk'
    assert app.locator('iframe[src*="youtube-nocookie.com/embed/abcdefghijk"]').count() == 1
