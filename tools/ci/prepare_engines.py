#!/usr/bin/env python3
"""Recreate committed inputs; require the reviewed license inventory before compiling."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
from update_bundled_apps import policy_for, policy_changes, preserve_notices

def run(script, *args):
    subprocess.run([sys.executable, str(ROOT/'tools'/script), *args], cwd=ROOT, check=True)

def main():
    run('fetch_play_sources.py')
    catalog = json.loads((ROOT/'tools/suite-lock.json').read_text())
    lock = json.loads((ROOT/'release/build-tools.json').read_text())
    fonts = [('craft-fonts', lock['craft-fonts'])] + [('craft-fonts-'+p['commit'], p) for p in lock.get('additionalFontInputs', [])]
    reviewed = json.loads((ROOT/'tools/bundled-license-policy.json').read_text())
    if policy_changes(reviewed, policy_for(ROOT, catalog, fonts)):
        raise ValueError('License/dependency inputs differ from the reviewed inventory. Review them before release.')
    run('prepare_suite.py')
    run('prepare_play_sources.py')
    run('build_play_engines.py')
    preserve_notices(ROOT, catalog, fonts)
    run('check_play_release.py', '--assets-only')
    # Build tools must reproduce pins, never silently refresh source locks in CI.
    subprocess.run(['git', 'diff', '--exit-code', '--', 'tools/play-source-lock.json', 'tools/suite-lock.json'], cwd=ROOT, check=True)

if __name__ == '__main__': main()
