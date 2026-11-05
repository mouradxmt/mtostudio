#!/usr/bin/env python3
"""Build a tiny signed FUTURE APK for verifier tests only. Never publish or install it."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
def main():
    sdk = Path(os.environ.get('ANDROID_HOME', str(ROOT/'.tools/android-sdk')))
    if not (sdk/'build-tools/36.0.0').is_dir(): sdk = ROOT/'.tools/android-sdk'
    tools = sdk/'build-tools/36.0.0'
    folder = ROOT/'.tools/update-fixture'; folder.mkdir(exist_ok=True)
    manifest = folder/'AndroidManifest.xml'
    manifest.write_text('''<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.mtouaa.studio.huawei" android:versionCode="10" android:versionName="0.6.1"><uses-sdk android:minSdkVersion="26" android:targetSdkVersion="36"/><application android:label="TEST FIXTURE ONLY" android:hasCode="false"/></manifest>''')
    unsigned = folder/'fixture-unsigned.apk'; target = folder/'fixture.apk'
    subprocess.run([str(tools/'aapt'), 'package', '-f', '-M', str(manifest), '-I', str(sdk/'platforms/android-37.0/android.jar'), '-F', str(unsigned)], check=True)
    props = dict(line.split('=',1) for line in (ROOT/'.release-secrets/upload.properties').read_text().splitlines() if line and not line.startswith('#'))
    env = dict(os.environ, JAVA_HOME=os.environ.get('JAVA_HOME',str(ROOT/'.tools/jdk-17.0.21+9/Contents/Home')))
    with tempfile.TemporaryDirectory(dir=ROOT/'.release-secrets') as temporary:
        passwords = []
        for key in ('storePassword', 'keyPassword'):
            path = Path(temporary)/key; path.write_text(props[key]); path.chmod(0o600); passwords.append('file:'+str(path))
        subprocess.run([str(tools/'apksigner'), 'sign', '--ks', str(ROOT/props['storeFile']), '--ks-key-alias', props['keyAlias'], '--ks-pass', passwords[0], '--key-pass', passwords[1], '--out', str(target), str(unsigned)], env=env, check=True)
    print('Verifier fixture only:', target)

if __name__ == '__main__': main()
