#!/usr/bin/env python3
"""Package verified publisher APKs/AAB and an APK-key-signed Huawei update descriptor."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import struct
import zipfile

ROOT = Path(__file__).resolve().parent.parent
SIGNER_SHA256 = 'c4388b1fc99fe8bf576970455a0f4089bffe8d272583f53500a8f8eee6dd1576'

def verify_apk(path, channel):
    sdk = sdk_home()/'build-tools/36.0.0'
    env = dict(os.environ, JAVA_HOME=os.environ.get('JAVA_HOME', str(ROOT/'.tools/jdk-17.0.21+9/Contents/Home')))
    cert = subprocess.check_output([str(sdk/'apksigner'), 'verify', '--print-certs', str(path)], text=True, env=env)
    fingerprints = re.findall(r'Signer #\d+ certificate SHA-256 digest: ([0-9a-f]+)', cert)
    if fingerprints != [SIGNER_SHA256]: raise ValueError('Unexpected release signing certificate')
    subprocess.run([str(sdk/'zipalign'), '-c', '-P', '16', '4', str(path)], check=True, env=env)
    badging = subprocess.check_output([str(sdk/'aapt'), 'dump', 'badging', str(path)], text=True)
    if 'application-debuggable' in badging: raise ValueError('Debuggable release APK')
    permissions = subprocess.check_output([str(sdk/'aapt'), 'dump', 'permissions', str(path)], text=True)
    if ('android.permission.REQUEST_INSTALL_PACKAGES' in permissions) != (channel == 'huawei'): raise ValueError('APK installer permission in wrong channel')
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.startswith('lib/') and name.endswith('.so'):
                data = archive.read(name)
                if data[:6] != b'\x7fELF\x02\x01': raise ValueError('Unexpected native format')
                offset = struct.unpack_from('<Q', data, 32)[0]; stride, count = struct.unpack_from('<HH', data, 54)
                align = [struct.unpack_from('<Q', data, offset+i*stride+48)[0] for i in range(count) if struct.unpack_from('<I', data, offset+i*stride)[0] == 1]
                if not align or min(align) < 16384: raise ValueError('Native library does not support 16 KB pages')

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def apk_info(path):
    sdk = sdk_home()
    aapt = sdk/'build-tools/36.0.0/aapt'
    line = subprocess.check_output([str(aapt), 'dump', 'badging', str(path)], text=True).splitlines()[0]
    fields = dict(re.findall(r"\b(name|versionCode|versionName)='([^']*)'", line))
    return fields

def sdk_home():
    sdk = Path(os.environ.get('ANDROID_HOME', str(ROOT/'.tools/android-sdk')))
    return sdk if (sdk/'build-tools/36.0.0').is_dir() else ROOT/'.tools/android-sdk'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default='mouradxmt/mtostudio')
    parser.add_argument('--output', default='dist/release')
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',args.repository): raise ValueError('Invalid release repository')
    build=ROOT/'app/build/outputs'
    huawei=build/'apk/huawei/release/app-huawei-release.apk'
    play=build/'apk/play/release/app-play-release.apk'
    bundle=build/'bundle/playRelease/app-play-release.aab'
    info=apk_info(huawei);play_info=apk_info(play)
    if info['name']!='com.mtouaa.studio.huawei' or play_info['name']!='com.mtouaa.studio': raise ValueError('Wrong application identity')
    version=info['versionName'];code=int(info['versionCode'])
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',version): raise ValueError('Stable release name required')
    if play_info['versionName']!=version or int(play_info['versionCode'])!=code: raise ValueError('Channel version mismatch')
    verify_apk(huawei,'huawei');verify_apk(play,'play')
    prefix='Mtouaa-Studio-'+version
    out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True)
    assets=[]
    for source,name in [(huawei,prefix+'-huawei.apk'),(play,prefix+'-play.apk'),(bundle,prefix+'-play.aab')]:
        target=out/name;shutil.copy2(source,target);assets.append(target)
    payload={'format':1,'channel':'huawei','applicationId':info['name'],'versionCode':code,'versionName':version,
        'apk':{'url':f'https://github.com/{args.repository}/releases/download/v{version}/{prefix}-huawei.apk',
               'size':huawei.stat().st_size,'sha256':sha(huawei)}}
    private=ROOT/'.release-secrets';private.mkdir(exist_ok=True)
    payload_file=private/'release-payload.json';signature_file=private/'release-signature.txt'
    payload_file.write_text(json.dumps(payload,sort_keys=True,separators=(',',':')));payload_file.chmod(0o600)
    java=Path(os.environ.get('JAVA_HOME', str(ROOT/'.tools/jdk-17.0.21+9/Contents/Home')))/'bin/java'
    subprocess.run([str(java),str(ROOT/'tools/ci/SignUpdate.java'),str(private/'upload.properties'),str(payload_file),str(signature_file)],cwd=ROOT,check=True)
    envelope={'format':1,'algorithm':'SHA256withRSA','payload':base64.b64encode(payload_file.read_bytes()).decode(),'signature':signature_file.read_text().strip()}
    metadata=out/'mtouaa-update.json';metadata.write_text(json.dumps(envelope,indent=2)+'\n');assets.append(metadata)
    (out/'SHA256SUMS.txt').write_text(''.join(sha(path)+'  '+path.name+'\n' for path in assets))
    shutil.copy2(ROOT/'release/VERIFICATION.md',out/'VERIFICATION.md')
    print('Packaged Mtouaa Studio',version,'code',code,'with an authenticated Huawei update descriptor.')

if __name__=='__main__':main()
