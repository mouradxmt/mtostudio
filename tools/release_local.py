#!/usr/bin/env python3
"""Build/sign a release locally from reviewed cached editors; optionally publish it."""
import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent

def run(*args, env=None):
    return subprocess.run([str(a) for a in args],cwd=ROOT,env=env,check=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish',action='store_true',help='Push the clean source/tag and publish the verified local package')
    args=parser.parse_args()
    text=(ROOT/'app/build.gradle').read_text()
    version=re.search(r"versionName '([0-9]+\.[0-9]+\.[0-9]+)'",text).group(1)
    tag='v'+version
    if args.publish:
        if subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=ROOT,text=True).strip():
            raise ValueError('Commit source changes before publishing a release')
    env=dict(os.environ)
    env['JAVA_HOME']=env.get('JAVA_HOME') or str(ROOT/'.tools/jdk-17.0.21+9/Contents/Home')
    env['PATH']=str(ROOT/'.tools/gh')+os.pathsep+env['PATH']
    env['GH_CONFIG_DIR']=str(ROOT/'.release-secrets/gh-config')
    env['GITHUB_REPOSITORY']='mouradxmt/mtostudio';env['RELEASE_REF']='refs/tags/'+tag;env['RELEASE_TAG']=tag
    run(sys.executable,'tools/ci/check_version.py',env=env)
    run(sys.executable,'tools/check_play_release.py','--assets-only',env=env)
    # No Rust compilation or upstream refresh: changed engines require the explicit
    # updateBundledApps maintenance task and its license review first.
    run('./tools/build.sh','--offline','assembleHuaweiRelease','assemblePlayRelease','bundlePlayRelease','lintHuaweiRelease','lintPlayRelease',env=env)
    run(sys.executable,'tools/verify_play_bundle.py',env=env)
    output='dist/releases/'+version
    run(sys.executable,'tools/package_release.py','--output',output,env=env)
    if args.publish:
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        existing=subprocess.run(['git','rev-parse','--verify','refs/tags/'+tag],cwd=ROOT,capture_output=True,text=True)
        if existing.returncode==0 and existing.stdout.strip()!=head:raise ValueError('Existing release tag points to another commit; use a new version')
        if existing.returncode!=0:run('git','tag',tag,env=env)
        helper='!'+shlex.quote(str(ROOT/'.tools/gh/gh'))+' auth git-credential'
        run('git','-c','credential.helper=','-c','credential.helper='+helper,'push','origin','HEAD:main','refs/tags/'+tag,env=env)
        # The publisher helper reads this fixed staging directory. Keep one copy
        # of each final binary; do not create CI artifacts or intermediate uploads.
        env['MTOUAA_RELEASE_DIR']=str(ROOT/output)
        run(sys.executable,'tools/ci/publish_release.py',env=env)
    print('Verified local release:',ROOT/output)

if __name__=='__main__':main()
