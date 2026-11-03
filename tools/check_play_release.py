#!/usr/bin/env python3
"""Fail closed if a Play build contains stock engines, changed outputs or unfinished metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent.parent
def validate_assets():
    catalog=json.loads((ROOT/'tools/suite-lock.json').read_text())
    pins={p['id']:p for p in json.loads((ROOT/'tools/play-source-lock.json').read_text())}
    dest=ROOT/'app/src/play/assets/suite'
    if not (dest/'catalog.json').is_file():raise ValueError('Rebranded suite is incomplete. Run tools/build_play_engines.py; stock web packages are not eligible for Play.')
    installed=json.loads((dest/'catalog.json').read_text())
    if len(catalog)!=15 or len(installed)!=15:raise ValueError('Expected exactly 15 editors')
    if {a['id'] for a in installed}!={a['id'] for a in catalog}:raise ValueError('Play catalog must contain all 15 tools')
    for app in catalog:
        folder=dest/app['id'];report=json.loads((folder/'mtouaa-build.json').read_text())
        if report['source']!=pins[app['id']]:raise ValueError('Unpinned source: '+app['id'])
        if 'version' in app and report['source'].get('version')!=app['version']:raise ValueError('Source version does not match the catalog: '+app['id'])
        if report['patch'].get('recipeSha256')!=hashlib.sha256((ROOT/'tools/prepare_play_sources.py').read_bytes()).hexdigest():raise ValueError('Engine must be rebuilt with the current branding recipe: '+app['id'])
        brand=json.loads((ROOT/'release/brand.json').read_text())
        if report['patch'].get('brand')!={key:brand[key] for key in ['appName','website']}:raise ValueError('Editor branding does not match the public configuration: '+app['id'])
        actual={str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p != folder/'mtouaa-build.json'}
        if actual != set(report['files']):raise ValueError('Unrecorded or missing engine output: '+app['id'])
        for name,digest in report['files'].items():
            p=folder/name
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise ValueError('Changed engine output: '+str(p))
        wasm=list(folder.glob('*.wasm'))+list(folder.glob('app/*.wasm'))
        if not wasm:raise ValueError('No compiled editor: '+app['id'])
        interface_files=[p for p in folder.rglob('*') if p.is_file() and p.suffix in ['.html','.js','.svg','.webmanifest']]
        for p in wasm + interface_files:
            raw=p.read_bytes()
            # The pinned sources name this team in their copyright statements.
            # Required plain-text author credits must survive rebranding.
            raw=raw.replace(b'ArtCraft Team',b'upstream authors')
            for forbidden in [b'ArtCraft',b'getartcraft.com',b'discord.gg/artcraft']:
                if forbidden in raw:raise ValueError('Embedded upstream branding remains in '+str(p)+': '+forbidden.decode())
        if not (folder/'MTOUAA-MODIFICATIONS.txt').is_file():raise ValueError('No modification notice')
    print('PASS: all 15 Play editors are built from pinned rebranded source; output hashes and branding scan verified.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--assets-only',action='store_true');parser.add_argument('--submission',action='store_true');args=parser.parse_args()
    try:
        validate_assets()
        if args.submission:
            brand=json.loads((ROOT/'release/brand.json').read_text())
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',brand['supportEmail']):raise ValueError('Create and configure a working support email in release/brand.json')
            if not (ROOT/'.release-secrets/upload.properties').is_file():raise ValueError('Upload signing key is not configured')
            status=json.loads((ROOT/'release/submission-status.json').read_text())
            pending=[name for name,done in status.items() if done is not True]
            if pending:raise ValueError('Submission tasks still pending: '+', '.join(pending))
    except (ValueError,KeyError,FileNotFoundError) as error:
        print('NOT READY: '+str(error),file=sys.stderr);sys.exit(1)
