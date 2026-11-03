#!/usr/bin/env python3
"""Create a local Play upload key once. Secrets never go into command arguments or source."""
import os
from pathlib import Path
import secrets
import subprocess

ROOT=Path(__file__).resolve().parent.parent
folder=ROOT/'.release-secrets'
folder.mkdir(mode=0o700,exist_ok=True)
key=folder/'mtouaa-upload.p12';props=folder/'upload.properties';password=folder/'password.tmp'
if key.exists() or props.exists():raise SystemExit('Upload key/config already exists; it was not overwritten.')
secret=secrets.token_urlsafe(36)
descriptor=os.open(password,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(descriptor,'w') as stream:stream.write(secret)
try:
    tool=ROOT/'.tools/jdk-17.0.21+9/Contents/Home/bin/keytool'
    subprocess.run([str(tool),'-genkeypair','-keystore',str(key),'-storetype','PKCS12','-alias','upload','-keyalg','RSA','-keysize','3072','-validity','10000','-dname','CN=Mtouaa Studio Upload','-storepass:file',str(password),'-keypass:file',str(password),'-noprompt'],check=True,stdout=subprocess.DEVNULL)
    os.chmod(key,0o600)
    descriptor=os.open(props,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'w') as stream:stream.write('storeFile=.release-secrets/mtouaa-upload.p12\nkeyAlias=upload\nstorePassword='+secret+'\nkeyPassword='+secret+'\n')
    print('Created local upload key and private Gradle config in .release-secrets/. Back up both securely.')
finally:
    password.unlink(missing_ok=True)
