#!/usr/bin/env python3
"""Bundle every pinned official web release. Runtime updates use the same archive layout."""
import concurrent.futures
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'app/src/main/assets/suite'
LIMIT = 2 * 1024 ** 3

def extract(archive, destination):
    with zipfile.ZipFile(archive) as bundle:
        entries = bundle.infolist()
        if len(entries) > 20000 or sum(max(0, e.file_size) for e in entries) > LIMIT:
            raise ValueError('Archive exceeds limits')
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in entry.filename:
                raise ValueError('Unsafe archive path')
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Archive symlinks are not supported')
        indexes = [PurePosixPath(e.filename) for e in entries if e.filename.endswith('index.html')]
        indexes.sort(key=lambda p: len(p.parts))
        if not indexes or (len(indexes) > 1 and len(indexes[0].parts) == len(indexes[1].parts)):
            raise ValueError('Missing or ambiguous app index')
        prefix = indexes[0].parent
        staging = destination.with_name(destination.name + '.staging')
        if staging.exists(): shutil.rmtree(staging)
        staging.mkdir(parents=True)
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if entry.is_dir(): continue
            # Android's asset merger treats name.gz as name; avoid duplicate precompressed variants.
            if entry.filename.endswith(('.gz', '.br')) and entry.filename.rsplit('.', 1)[0] in bundle.namelist():
                continue
            try: relative = path.relative_to(prefix)
            except ValueError: raise ValueError('Files outside application root')
            target = staging / str(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(entry) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)
        index = staging / 'index.html'
        html = index.read_text()
        html, count = re.subn(r'<head\b[^>]*>', lambda m: m[0] + '\n<script src="/__native-save.js"></script>', html, count=1, flags=re.I)
        if count != 1: raise ValueError('Missing HTML head')
        index.write_text(html)
        if destination.exists(): shutil.rmtree(destination)
        staging.rename(destination)

def prepare(app):
    if 'url' not in app: return app
    archive = ROOT / 'vendor' / app['asset']
    archive.parent.mkdir(exist_ok=True)
    if not archive.exists():
        print('Downloading ' + app['name'], flush=True)
        request = urllib.request.Request(app['url'], headers={'User-Agent': 'ArtCraft-Offline-Android'})
        partial = archive.with_suffix('.partial')
        with urllib.request.urlopen(request, timeout=120) as source, partial.open('wb') as output:
            shutil.copyfileobj(source, output)
        partial.rename(archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != app['sha256']: raise ValueError(app['id'] + ': checksum mismatch')
    destination = DEST / app['id']
    stamp = destination / '.bundle-sha256'
    if not stamp.exists() or stamp.read_text() != digest + '-bundle2':
        extract(archive, destination)
        stamp.write_text(digest + '-bundle2')
    print('Bundled ' + app['name'] + ' ' + app['version'], flush=True)
    return app

def main():
    catalog = json.loads((ROOT / 'tools/suite-lock.json').read_text())
    DEST.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(prepare, catalog))
    (DEST / 'catalog.json').write_text(json.dumps(catalog, indent=2) + '\n')
    legacy = ROOT / 'app/src/main/assets/editor'
    if legacy.exists(): shutil.rmtree(legacy)
    print('Suite ready: ' + str(len(catalog)) + ' apps')

if __name__ == '__main__': main()
