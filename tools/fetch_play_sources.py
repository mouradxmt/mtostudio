#!/usr/bin/env python3
"""Fetch immutable source commits for the pinned engines before Play rebranding."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'vendor/sources'
LOCK = ROOT / 'tools/play-source-lock.json'

def request(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'offline-suite-source-build'}), timeout=120)

def extract_archive(archive, folder):
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    marker = folder / '.mtouaa-source-archive.sha256'
    if marker.is_file() and marker.read_text().strip() == digest: return
    # A changed version must replace the cached source tree, rather than keeping
    # the previous release while recording the new commit in its provenance.
    with tempfile.TemporaryDirectory(prefix='.extract-', dir=folder.parent) as temporary:
        stage = Path(temporary) / 'source'
        stage.mkdir()
        with tarfile.open(archive) as source:
            members = source.getmembers()
            prefix = members[0].name.split('/')[0] + '/'
            for member in members:
                if not member.name.startswith(prefix): continue
                relative = Path(member.name[len(prefix):])
                if relative.is_absolute() or '..' in relative.parts: raise ValueError('Unsafe source archive path')
                if member.issym() or member.islnk(): continue
                target = stage / relative
                if member.isdir(): target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.extractfile(member) as stream: target.write_bytes(stream.read())
        (stage / marker.name).write_text(digest + '\n')
        if folder.exists(): shutil.rmtree(folder)
        stage.rename(folder)

def fetch_fonts():
    tools = json.loads((ROOT / 'release/build-tools.json').read_text())
    for index, pin in enumerate([tools['craft-fonts']] + tools['additionalFontInputs']):
        name = 'craft-fonts' if index == 0 else 'craft-fonts-' + pin['commit']
        archive = DEST / (name + '.tar.gz')
        if not archive.exists():
            with request('https://codeload.github.com/storytold/craft-fonts/tar.gz/' + pin['commit']) as response:
                archive.write_bytes(response.read())
        if hashlib.sha256(archive.read_bytes()).hexdigest() != pin['sha256']:
            raise ValueError('Font archive checksum mismatch: ' + name)
        extract_archive(archive, DEST / name)
        print(name + ' source ' + pin['commit'], flush=True)
    for pin in tools.get('additionalSourceInputs', []):
        if pin['repo'] != 'storytold/craft-i18n': raise ValueError('Unsupported additional source input')
        name = 'craft-i18n-' + pin['commit']
        archive = DEST / (name + '.tar.gz')
        if not archive.exists():
            with request('https://codeload.github.com/' + pin['repo'] + '/tar.gz/' + pin['commit']) as response:
                archive.write_bytes(response.read())
        if hashlib.sha256(archive.read_bytes()).hexdigest() != pin['sha256']: raise ValueError('Additional source checksum mismatch: ' + name)
        extract_archive(archive, DEST / name)
        print(name + ' source ' + pin['commit'], flush=True)

def fetch(app):
    pin = next((p for p in pins if p['id'] == app['id'] and p['version'] == app['version']), None)
    if pin is None:
        with request(f"https://api.github.com/repos/{app['repo']}/git/ref/tags/v{app['version']}") as response:
            obj = json.load(response)['object']
        while obj['type'] == 'tag':
            with request(obj['url']) as response: obj = json.load(response)['object']
        if obj['type'] != 'commit': raise ValueError('Expected commit')
        pin = {'id': app['id'], 'repo': app['repo'], 'version': app['version'], 'commit': obj['sha']}
    archive = DEST / (app['id'] + '-' + pin['commit'] + '.tar.gz')
    if not archive.exists():
        with request(f"https://codeload.github.com/{app['repo']}/tar.gz/{pin['commit']}") as response:
            archive.write_bytes(response.read())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if 'sha256' in pin and pin['sha256'] != digest: raise ValueError('Source archive checksum mismatch')
    pin['sha256'] = digest
    extract_archive(archive, DEST / app['id'])
    print(app['id'] + ' source ' + pin['commit'], flush=True)
    return pin

if __name__ == '__main__':
    DEST.mkdir(parents=True, exist_ok=True)
    pins = json.loads(LOCK.read_text()) if LOCK.exists() else []
    catalog = json.loads((ROOT / 'tools/suite-lock.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        result = list(pool.map(fetch, catalog))
    LOCK.write_text(json.dumps(result, indent=2) + '\n')
    fetch_fonts()
