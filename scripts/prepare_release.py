"""Empaqueta únicamente los recursos públicos del SHA que acaba de pasar los tests."""
import argparse
import hashlib
import json
import pathlib
import re
import shutil

ASSETS = ('index.html', 'config.js', 'sw.js', 'manifest.webmanifest',
          'icon-192.png', 'icon-512.png', 'apple-touch-icon.png')
GUIDES = tuple(f'guia/{lang}-{page}.jpg' for lang in ('es', 'en') for page in (1, 2, 3))


def prepare_release(root, destination, sha):
    root, destination = pathlib.Path(root), pathlib.Path(destination)
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('Se requiere el SHA completo del commit probado')
    paths = ASSETS + GUIDES
    for name in paths:
        source = root / name
        if not source.is_file() or source.is_symlink() or source.stat().st_size == 0:
            raise ValueError(f'Recurso público ausente o inválido: {name}')
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('La carpeta de publicación debe estar vacía')
    destination.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in paths:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest = {'sha': sha, 'assets': hashes}
    (destination / 'release.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--output', default='_site')
    args = parser.parse_args()
    prepare_release(pathlib.Path(__file__).resolve().parent.parent, args.output, args.sha)
