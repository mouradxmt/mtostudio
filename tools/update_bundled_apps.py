#!/usr/bin/env python3
"""Explicit, staged maintenance of the 15 bundled editors, never an in-app updater."""
import argparse
import concurrent.futures
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from urllib.parse import quote

import discover_suite
import fetch_play_sources
import prepare_suite

ROOT = Path(__file__).resolve().parent.parent
POLICY = 'tools/bundled-license-policy.json'
REPORT = '.tools/bundled-update'
LEGAL_PREFIXES = ('LICENSE', 'LICENCE', 'NOTICE', 'COPYING', 'COPYRIGHT', 'OFL', 'ATTRIBUTION', 'AUTHORS', 'PATENTS')


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): result.update(block)
    return result.hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def read_json(path): return json.loads(path.read_text())


def github(url):
    headers = {'User-Agent': 'Mtouaa-Studio-bundle-maintenance', 'Accept': 'application/vnd.github+json'}
    # Never log the token or pass it on command lines / to archive hosts.
    if os.environ.get('GITHUB_TOKEN'): headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code in (403, 429):
            raise ValueError('GitHub API access was limited (HTTP ' + str(error.code) + '). Set GITHUB_TOKEN in your environment or retry after the rate limit resets; never commit the token.') from error
        raise


def latest(app):
    repo = app['repo']; slug = app['id']
    if repo != 'storytold/' + slug: raise ValueError('Unexpected upstream repository: ' + repo)
    release = github(f'https://api.github.com/repos/{repo}/releases/latest')
    tag = release['tag_name']
    if release.get('draft') or release.get('prerelease') or not re.fullmatch(r'v?\d+\.\d+\.\d+', tag):
        raise ValueError(slug + ': expected a stable semantic release')
    version = tag.lstrip('v')
    asset = [a for a in release['assets'] if a['name'] == f'{slug}-web-{version}.zip']
    if len(asset) != 1: raise ValueError(slug + ': latest release has no unique supported web archive; no silent fallback')
    asset = asset[0]; checksum = asset.get('digest', '')
    expected = f'https://github.com/{repo}/releases/download/{tag}/{asset["name"]}'
    if asset['browser_download_url'] != expected or not isinstance(checksum, str) or not re.fullmatch(r'sha256:[a-f0-9]{64}', checksum):
        raise ValueError(slug + ': invalid archive URL or missing SHA-256 digest')
    result = {key: app[key] for key in ('id', 'name', 'description', 'repo')}
    result.update(version=version, asset=asset['name'], url=expected, sha256=checksum[7:], size=asset['size'])
    if tuple(map(int, version.split('.'))) < tuple(map(int, app['version'].split('.'))):
        raise ValueError(slug + ': latest endpoint would downgrade the pinned version')
    obj = github(f'https://api.github.com/repos/{repo}/git/ref/tags/{quote(tag, safe="")}')['object']
    for _ in range(8):
        if obj['type'] != 'tag': break
        if not re.fullmatch('[a-f0-9]{40}', obj['sha']): raise ValueError('Invalid tag object')
        obj = github(f'https://api.github.com/repos/{repo}/git/tags/{obj["sha"]}')['object']
    if obj['type'] != 'commit' or not re.fullmatch('[a-f0-9]{40}', obj['sha']): raise ValueError('Invalid release commit')
    return result, {'id': slug, 'repo': repo, 'version': version, 'commit': obj['sha']}


def is_legal(path):
    return path.name.upper().startswith(LEGAL_PREFIXES) or any(p.lower() in ('licenses', 'licences', 'legal', 'contributors') for p in path.parts)


def inventory(source):
    # Cargo manifests/locks detect new dependencies even if upstream forgot to update notices.
    # Workflow and font manifest capture build inputs that can embed different font assets.
    files = {}
    for path in sorted(source.rglob('*')):
        relative = path.relative_to(source)
        if path.is_file() and (is_legal(relative) or path.name in ('Cargo.lock', 'Cargo.toml', 'deny.toml', 'manifest.txt') or str(relative) == '.github/workflows/release.yml'):
            files[str(relative)] = digest(path)
    return files


def policy_for(stage, catalog, fonts):
    for app in catalog:
        source = stage / 'vendor/sources' / app['id']
        for name in ('LICENSE-MIT', 'LICENSE-APACHE', 'NOTICE', 'Cargo.toml', 'Cargo.lock'):
            if not (source / name).is_file(): raise ValueError(app['id'] + ': missing required source/legal input ' + name)
        if not re.search(r'^license\s*=\s*"MIT OR Apache-2\.0"\s*$', (source / 'Cargo.toml').read_text(), re.M):
            raise ValueError(app['id'] + ': top-level license changed; update the licensing/notice implementation before proceeding')
    for name, pin in fonts:
        if not any(is_legal(p.relative_to(stage / 'vendor/sources' / name)) for p in (stage / 'vendor/sources' / name).rglob('*') if p.is_file()):
            raise ValueError('Missing font license records: ' + pin['commit'])
    return {'format': 1, 'inputs': {
        **{app['id']: inventory(stage / 'vendor/sources' / app['id']) for app in catalog},
        **{'font:' + pin['commit']: inventory(stage / 'vendor/sources' / name) for name, pin in fonts}
    }}


def policy_changes(old, new):
    changes = {}
    for name in sorted(set(old['inputs']) | set(new['inputs'])):
        before = old['inputs'].get(name, {}); after = new['inputs'].get(name, {})
        changed = [p for p in sorted(set(before) | set(after)) if before.get(p) != after.get(p)]
        if changed: changes[name] = changed
    return changes


def cache_files(stage):
    # Only immutable download archives are shared; extracted sources and output trees are isolated.
    for pattern in ('vendor/*.zip', 'vendor/sources/*.tar.gz'):
        for path in ROOT.glob(pattern):
            target = stage / path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
            os.link(path, target)


def configure_stage(stage):
    if stage.exists(): shutil.rmtree(stage)
    for directory in ('tools', 'release'):
        shutil.copytree(ROOT / directory, stage / directory, ignore=shutil.ignore_patterns('__pycache__'))
    for relative in ('app/src/play/assets/THIRD_PARTY_NOTICES.txt',):
        target = stage / relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / relative, target)
    (stage / '.tools').mkdir(exist_ok=True)
    for name in ('cargo', 'rustup', 'wasm-bin', 'cache', 'play-target'):
        target = ROOT / '.tools' / name
        if name in ('cache', 'play-target'): target.mkdir(exist_ok=True)
        if not target.exists(): raise ValueError('Missing build prerequisite .tools/' + name + '; see release/build-tools.json')
        (stage / '.tools' / name).symlink_to(target, target_is_directory=True)
    cache_files(stage)


def stage_inputs(stage, catalog, pins):
    write_json(stage / 'tools/suite-lock.json', catalog)
    previous = {p['id']: p for p in read_json(ROOT / 'tools/play-source-lock.json')}
    # Retagging an already pinned version is never silently accepted.
    for pin in pins:
        old = previous[pin['id']]
        if pin['version'] == old['version'] and pin['commit'] != old['commit']:
            raise ValueError(pin['id'] + ': pinned release tag moved; investigate upstream')
        if pin['commit'] == old['commit']: pin['sha256'] = old['sha256']
    fetch_play_sources.ROOT = stage
    fetch_play_sources.DEST = stage / 'vendor/sources'; fetch_play_sources.DEST.mkdir(parents=True, exist_ok=True)
    fetch_play_sources.pins = pins
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        pins = list(pool.map(fetch_play_sources.fetch, catalog))
    write_json(stage / 'tools/play-source-lock.json', pins)
    tools = read_json(stage / 'release/build-tools.json')
    known = {p['commit'] for p in [tools['craft-fonts']] + tools['additionalFontInputs']}
    for app in catalog:
        workflow = stage / 'vendor/sources' / app['id'] / '.github/workflows/release.yml'
        text = workflow.read_text() if workflow.is_file() else ''
        refs = re.findall(r'craft-fonts-ref:\s*([^\s#]+)', text)
        for ref in refs:
            if not re.fullmatch('[a-f0-9]{40}', ref): raise ValueError('Unpinned font input in ' + app['id'])
            if ref not in known:
                archive = stage / 'vendor/sources' / ('craft-fonts-' + ref + '.tar.gz')
                partial = archive.with_suffix('.download')
                with fetch_play_sources.request('https://codeload.github.com/storytold/craft-fonts/tar.gz/' + ref) as stream, partial.open('wb') as output:
                    shutil.copyfileobj(stream, output)
                partial.replace(archive)
                tools['additionalFontInputs'].append({'commit': ref, 'sha256': digest(archive)})
                known.add(ref)
    write_json(stage / 'release/build-tools.json', tools)
    fetch_play_sources.fetch_fonts()
    fonts = [('craft-fonts', tools['craft-fonts'])] + [('craft-fonts-' + p['commit'], p) for p in tools['additionalFontInputs']]
    return pins, fonts


def preserve_notices(stage, catalog, fonts):
    """Keep original legal trees intact, separately from the artwork-adjusted attribution."""
    for app in catalog:
        target = stage / 'app/src/play/assets/suite' / app['id']
        legal = target / 'upstream-legal'
        if legal.exists(): shutil.rmtree(legal)
        sources = [('source', stage / 'vendor/sources' / app['id'])]
        sources += [('fonts/' + pin['commit'], stage / 'vendor/sources' / name) for name, pin in fonts]
        for prefix, source in sources:
            for path in source.rglob('*'):
                relative = path.relative_to(source)
                if path.is_file() and is_legal(relative):
                    output = legal / prefix / relative; output.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, output)
        # Include the immutable source and original top-level legal text in the visible About dialog.
        report_path = target / 'mtouaa-build.json'; report = read_json(report_path)
        report['files'] = {str(p.relative_to(target)): digest(p) for p in sorted(target.rglob('*')) if p.is_file() and p != report_path}
        write_json(report_path, report)
    notices = stage / 'app/src/play/assets/THIRD_PARTY_NOTICES.txt'
    base = notices.read_text().split('\n--- Bundled editor source notices ---')[0]
    parts = [base, '\n--- Bundled editor source notices ---\n']
    pins = {p['id']: p for p in read_json(stage / 'tools/play-source-lock.json')}
    for app in catalog:
        pin = pins[app['id']]
        parts.append(f'\n{app["name"]} {app["version"]}\nhttps://github.com/{app["repo"]}/tree/{pin["commit"]}\n')
        for path in sorted((stage / 'vendor/sources' / app['id']).iterdir()):
            if path.is_file() and path.name.upper().startswith(('LICENSE', 'LICENCE', 'NOTICE')):
                parts.append('\n' + path.name + '\n' + path.read_text())
    text = '\n'.join(parts)
    if len(text.encode('utf-8')) > 1024 * 1024:
        raise ValueError('Combined visible notices exceed the Android About reader limit; extend the notices UI before updating')
    notices.write_text(text)


def promote(stage, paths, backup, replace=os.replace):
    """Rollback every published path if any rename fails. Keep backups after success."""
    moved = []; installed = []
    try:
        for relative in paths:
            current = ROOT / relative; saved = backup / relative; candidate = stage / relative
            if not candidate.exists(): raise ValueError('Missing staged output: ' + relative)
            saved.parent.mkdir(parents=True, exist_ok=True); current.parent.mkdir(parents=True, exist_ok=True)
            if current.exists(): replace(current, saved); moved.append((saved, current))
            replace(candidate, current); installed.append(current)
    except BaseException:
        for path in reversed(installed):
            if path.is_dir(): shutil.rmtree(path)
            else: path.unlink()
        for saved, current in reversed(moved): os.replace(saved, current)
        raise


def run(args):
    report_dir = ROOT / REPORT; report_dir.mkdir(parents=True, exist_ok=True)
    old = read_json(ROOT / 'tools/suite-lock.json')
    if {a['id'] for a in old} != {a[0] for a in discover_suite.APPS} or len(old) != 15:
        raise ValueError('Expected the existing 15 official editors')
    write_json(report_dir / 'report.json', {'status': 'discovering'})
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        found = list(pool.map(latest, old))
    catalog, pins = map(list, zip(*found))
    report = {'status': 'discovered', 'editors': [dict(id=a['id'], previous=b['version'], latest=a['version'], commit=p['commit']) for a,b,p in zip(catalog,old,pins)],
              'scope': '15 bundled editors and their upstream-pinned font inputs; Android/Gecko/toolchain dependencies remain pinned'}
    write_json(report_dir / 'report.json', report)
    for app, previous in zip(catalog, old): print(f'{app["id"]}: {previous["version"]} -> {app["version"]}', flush=True)
    if args.check:
        print('Discovery only; locks and bundled assets unchanged. See ' + str(report_dir / 'report.json')); return
    stage = report_dir / 'workspace'; configure_stage(stage)
    pins, fonts = stage_inputs(stage, catalog, pins)
    policy = policy_for(stage, catalog, fonts)
    write_json(report_dir / 'candidate-license-policy.json', policy)
    changes = policy_changes(read_json(ROOT / POLICY), policy)
    report.update(status='license-review-required' if changes else 'inputs-verified', licenseChanges=changes)
    write_json(report_dir / 'report.json', report)
    if changes:
        raise ValueError('License/attribution/dependency/build inputs changed. Review report.json and staged sources; after review, replace tools/bundled-license-policy.json with candidate-license-policy.json. Rerun to revalidate exact inputs. Current bundle unchanged.')
    prepare_suite.ROOT = stage; prepare_suite.DEST = stage / 'app/src/main/assets/suite'
    prepare_suite.main()
    # Reuse only outputs whose source and patch report remain valid; the builder checks all hashes.
    source_assets = ROOT / 'app/src/play/assets/suite'
    if source_assets.exists(): shutil.copytree(source_assets, stage / 'app/src/play/assets/suite')
    for command in ('prepare_play_sources.py', 'build_play_engines.py'):
        subprocess.run([sys.executable, str(stage / 'tools' / command)], cwd=stage, check=True)
    preserve_notices(stage, catalog, fonts)
    subprocess.run([sys.executable, str(stage / 'tools/check_play_release.py'), '--assets-only'], cwd=stage, check=True)
    backup = report_dir / 'previous'
    if backup.exists(): shutil.rmtree(backup)
    promote(stage, ['tools/suite-lock.json', 'tools/play-source-lock.json', 'release/build-tools.json',
                    'app/src/main/assets/suite', 'app/src/play/assets/suite', 'app/src/play/assets/THIRD_PARTY_NOTICES.txt',
                    'vendor/sources', '.tools/play-work'], backup)
    report.update(status='updated', runtimeTests='Not run; build APK/AAB and run device import/menu/offline checks before release.')
    write_json(report_dir / 'report.json', report)
    print('Updated and verified all 15 editors. Previous files: ' + str(backup))
    print('Review git diff, bump Android version, build and run device checks before publishing.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Discover stable versions only, without downloads/builds or lock changes')
    args = parser.parse_args()
    lock = ROOT / '.tools/bundled-update.lock'; lock.parent.mkdir(exist_ok=True)
    with lock.open('w') as stream:
        try: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: parser.exit(1, 'Another bundled update is already running.\n')
        try: run(args)
        except (Exception, KeyboardInterrupt) as error:
            path = ROOT / REPORT / 'report.json'
            report = read_json(path) if path.is_file() else {}
            report.update(error=str(error))
            if report.get('status') != 'license-review-required': report['status'] = 'failed'
            write_json(path, report)
            parser.exit(1, 'UPDATE STOPPED: ' + str(error) + '\n')


if __name__ == '__main__': main()
