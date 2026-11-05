#!/usr/bin/env python3
"""Recreate committed inputs; require the reviewed license inventory before compiling."""
import json
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
from update_bundled_apps import policy_for, policy_changes, preserve_notices
import prepare_suite
from prepare_play_sources import NAMES

def run(script, *args):
    subprocess.run([sys.executable, str(ROOT/'tools'/script), *args], cwd=ROOT, check=True)

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--app'); parser.add_argument('--notices-only',action='store_true'); args=parser.parse_args()
    run('fetch_play_sources.py')
    catalog = json.loads((ROOT/'tools/suite-lock.json').read_text())
    lock = json.loads((ROOT/'release/build-tools.json').read_text())
    fonts = [('craft-fonts', lock['craft-fonts'])] + [('craft-fonts-'+p['commit'], p) for p in lock.get('additionalFontInputs', [])]
    reviewed = json.loads((ROOT/'tools/bundled-license-policy.json').read_text())
    if policy_changes(reviewed, policy_for(ROOT, catalog, fonts)):
        raise ValueError('License/dependency inputs differ from the reviewed inventory. Review them before release.')
    selected = [app for app in catalog if not args.app or app['id']==args.app]
    if not selected: raise ValueError('Unknown editor')
    if not args.notices_only:
        if args.app:
            prepare_suite.prepare(selected[0])
            run('prepare_play_sources.py','--app',args.app)
            run('build_play_engines.py','--app',args.app)
        else:
            run('prepare_suite.py'); run('prepare_play_sources.py'); run('build_play_engines.py')
    preserve_notices(ROOT, selected, fonts)
    if not args.app:
        for app in catalog:
            app['alias']=''.join(c for c in app['name'] if c.isalnum()); app['name']=NAMES[app['id']]
        (ROOT/'app/src/play/assets/suite/catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
        run('check_play_release.py', '--assets-only')
    # Build tools must reproduce pins, never silently refresh source locks in CI.
    subprocess.run(['git', 'diff', '--exit-code', '--', 'tools/play-source-lock.json', 'tools/suite-lock.json'], cwd=ROOT, check=True)

if __name__ == '__main__': main()
