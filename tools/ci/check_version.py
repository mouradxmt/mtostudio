#!/usr/bin/env python3
"""Reject tags that would publish the wrong application/version/feed repository."""
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
def main():
    text = (ROOT/'app/build.gradle').read_text()
    version = re.search(r"versionName '([0-9]+\.[0-9]+\.[0-9]+)'", text).group(1)
    code = int(re.search(r'versionCode (\d+)', text).group(1))
    if code <= 8 or code > 2100000000: raise ValueError('Release code must exceed previously shipped version 8')
    ref = os.environ.get('RELEASE_REF', '')
    if ref.startswith('refs/tags/') and ref != 'refs/tags/v'+version: raise ValueError('Tag does not match app version')
    if ref.startswith('refs/tags/'):
        for tag in subprocess.check_output(['git','tag','--merged','HEAD','--list','v*'],cwd=ROOT,text=True).splitlines():
            if tag == 'v'+version: continue
            previous = subprocess.check_output(['git','show',tag+':app/build.gradle'],cwd=ROOT,text=True)
            previous_code = int(re.search(r'versionCode (\d+)',previous).group(1))
            if previous_code >= code: raise ValueError('Release versionCode must exceed all previous release tags')
    repo = os.environ.get('GITHUB_REPOSITORY', 'mouradxmt/mtostudio')
    if repo != 'mouradxmt/mtostudio': raise ValueError('Update feed is configured for mouradxmt/mtostudio; review configuration before publishing elsewhere')
    print('Mtouaa Studio', version, 'code', code)

if __name__ == '__main__': main()
