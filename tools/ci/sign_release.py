#!/usr/bin/env python3
"""Materialize CI signing secrets privately, then sign the already-built artifacts."""
import base64
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]

def main():
    private = ROOT/'.release-secrets'; private.mkdir(mode=0o700, exist_ok=True)
    values = {key: os.environ[key] for key in ('ANDROID_STORE_PASSWORD', 'ANDROID_KEY_ALIAS', 'ANDROID_KEY_PASSWORD')}
    if any(not value or '\n' in value or '\r' in value for value in values.values()): raise ValueError('Invalid signing configuration')
    key = private/'mtouaa-upload.p12'
    key.write_bytes(base64.b64decode(os.environ['ANDROID_KEYSTORE_BASE64'], validate=True)); key.chmod(0o600)
    # Properties escaping preserves literal punctuation in generated passwords.
    def escape(value): return value.replace('\\', '\\\\').replace(' ', '\\ ').replace('=', '\\=').replace(':', '\\:')
    props = {'storeFile':'.release-secrets/mtouaa-upload.p12', 'storePassword':values['ANDROID_STORE_PASSWORD'], 'keyAlias':values['ANDROID_KEY_ALIAS'], 'keyPassword':values['ANDROID_KEY_PASSWORD']}
    properties = private/'upload.properties'
    properties.write_text(''.join(k+'='+escape(v)+'\n' for k,v in props.items())); properties.chmod(0o600)
    sdk = Path(os.environ['ANDROID_HOME'])/'build-tools/36.0.0'
    java = Path(os.environ['JAVA_HOME'])/'bin'
    for flavor in ('huawei', 'play'):
        folder = ROOT/f'app/build/outputs/apk/{flavor}/release'
        source = folder/f'app-{flavor}-release-unsigned.apk'; target = folder/f'app-{flavor}-release.apk'
        subprocess.run([str(sdk/'apksigner'), 'sign', '--ks', str(key), '--ks-key-alias', props['keyAlias'], '--ks-pass', 'env:ANDROID_STORE_PASSWORD', '--key-pass', 'env:ANDROID_KEY_PASSWORD', '--out', str(target), str(source)], check=True)
    bundle = ROOT/'app/build/outputs/bundle/playRelease/app-play-release.aab'
    subprocess.run([str(java/'jarsigner'), '-keystore', str(key), '-storetype', 'PKCS12', '-storepass:env', 'ANDROID_STORE_PASSWORD', '-keypass:env', 'ANDROID_KEY_PASSWORD', str(bundle), props['keyAlias']], check=True)

if __name__ == '__main__': main()
