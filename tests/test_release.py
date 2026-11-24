"""Regresiones del artefacto y de la espera del despliegue, sin red ni datos reales."""
import importlib.util
import pathlib
import sys
import re
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_release import ASSETS, GUIDES, prepare_release


@pytest.fixture
def site(tmp_path):
    root = tmp_path / 'source'
    for name in ASSETS + GUIDES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'recurso sintetico')
    return root


def test_artefacto_solo_contiene_recursos_publicos(site, tmp_path):
    (site / 'schema.sql').write_text('datos sintéticos que no se deben publicar')
    (site / '.env').write_text('marcador sintético')
    out = tmp_path / 'artifact'
    manifest = prepare_release(site, out, 'a' * 40)
    files = {str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()}
    assert files == set(ASSETS + GUIDES) | {'release.json'}
    assert manifest['sha'] == 'a' * 40
    import hashlib
    assert manifest['assets']['index.html'] == hashlib.sha256((out / 'index.html').read_bytes()).hexdigest()


def test_artefacto_rechaza_recurso_ausente(site, tmp_path):
    (site / 'config.js').unlink()
    with pytest.raises(ValueError, match='config.js'):
        prepare_release(site, tmp_path / 'artifact', 'a' * 40)


def test_artefacto_rechaza_sha_incompleto(site, tmp_path):
    with pytest.raises(ValueError, match='SHA completo'):
        prepare_release(site, tmp_path / 'artifact', 'abc123')


def test_artefacto_no_reutiliza_ficheros_de_otra_release(site, tmp_path):
    out = tmp_path / 'artifact'
    prepare_release(site, out, 'a' * 40)
    with pytest.raises(ValueError, match='vacía'):
        prepare_release(site, out, 'b' * 40)


def live_module():
    spec = importlib.util.spec_from_file_location('live_release', ROOT / 'tests/test_live.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Response:
    status = 200
    def __init__(self, sha):
        self.sha = sha
    def json(self):
        return {'sha': self.sha, 'assets': {'index.html': 'c' * 64}}


def test_smoke_espera_la_revision_esperada():
    module = live_module()
    calls = []
    versions = iter(['a' * 40, 'b' * 40])
    def request(url, **kwargs):
        calls.append(url)
        return Response(next(versions))
    manifest = module.wait_release('https://example.invalid/', 'b' * 40, request, pause=lambda _: None, attempts=2)
    assert manifest['sha'] == 'b' * 40
    assert len(calls) == 2 and calls[0] != calls[1]


def test_smoke_falla_si_sigue_publicada_la_revision_anterior():
    module = live_module()
    with pytest.raises(AssertionError, match='revisión esperada'):
        module.wait_release('https://example.invalid/', 'b' * 40,
                            lambda *a, **k: Response('a' * 40), pause=lambda _: None, attempts=2)


def test_publicacion_depende_de_tests_y_solo_admite_push_a_main():
    # Contrato de seguridad del workflow: las dependencias son escalares en este YAML.
    workflow = (ROOT / '.github/workflows/pruebas.yml').read_text()
    jobs = dict(re.findall(r'(?ms)^  ([a-z_]+):\n(.*?)(?=^  [a-z_]+:|\Z)', workflow))
    def ancestors(job):
        match = re.search(r'^    needs: ([a-z_]+)$', jobs[job], re.M)
        return {match[1]} | ancestors(match[1]) if match else set()
    assert 'pruebas' in ancestors('publicar')
    assert 'publicar' in ancestors('smoke')
    for job in ('empaquetar', 'publicar', 'smoke'):
        assert "    if: github.event_name == 'push' && github.ref == 'refs/heads/main'" in jobs[job]
    assert 'pages: write' not in jobs['pruebas']
    assert 'pull_request_target' not in workflow
