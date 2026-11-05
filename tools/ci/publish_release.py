#!/usr/bin/env python3
"""Resume draft uploads; never overwrite an already published release."""
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
def main():
    tag=os.environ['RELEASE_TAG'];repo=os.environ['GITHUB_REPOSITORY']
    if not re.fullmatch(r'v\d+\.\d+\.\d+',tag) or repo!='mouradxmt/mtostudio': raise ValueError('Unexpected release destination')
    def gh(*args,**kwargs):return subprocess.run(['gh',*args,'--repo',repo],check=True,**kwargs)
    existing=subprocess.run(['gh','release','view',tag,'--repo',repo,'--json','isDraft'],capture_output=True,text=True)
    if existing.returncode==0:
        if not json.loads(existing.stdout)['isDraft']: raise ValueError('Release is already public; refusing to overwrite published assets')
    else:
        gh('release','create',tag,'--draft','--verify-tag','--title','Mtouaa Studio '+tag,'--notes-file',str(ROOT/'release/RELEASE_NOTES.md'))
    files=sorted(Path(os.environ.get('MTOUAA_RELEASE_DIR',str(ROOT/'dist/release'))).glob('*'))
    if not files or not any(p.name=='mtouaa-update.json' for p in files): raise ValueError('Missing verified release package')
    gh('release','upload',tag,*(str(p) for p in files),'--clobber')
    gh('release','edit',tag,'--draft=false','--latest')

if __name__=='__main__':main()
