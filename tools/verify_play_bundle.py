#!/usr/bin/env python3
"""Validate the signed AAB and build an installable APK from that exact bundle.

Upload-key passwords are read locally and passed in private temporary files.
No credentials are written to the report or command-line arguments.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
JAVA_HOME = ROOT / '.tools/jdk-17.0.21+9/Contents/Home'
JAVA = JAVA_HOME / 'bin/java'
TOOLS = ROOT / '.tools/android-sdk/build-tools/36.0.0'
BUNDLETOOL = ROOT / '.tools/bundletool.jar'
BUNDLE = ROOT / 'app/build/outputs/bundle/playRelease/app-play-release.aab'
DEST = ROOT / '.tools/play-verification'
DEST.mkdir(parents=True, exist_ok=True)
ENV = dict(os.environ, JAVA_HOME=str(JAVA_HOME))

def run(args):
    return subprocess.run([str(a) for a in args], check=True, text=True,
                          capture_output=True, env=ENV).stdout.strip()

def bundletool(*args):
    return run([JAVA, '-jar', BUNDLETOOL, *args])

def elf_load_alignments(data):
    if data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('Expected a little-endian ELF64 native library')
    offset = struct.unpack_from('<Q', data, 32)[0]
    entry_size, count = struct.unpack_from('<HH', data, 54)
    return [struct.unpack_from('<Q', data, offset + i * entry_size + 48)[0]
            for i in range(count)
            if struct.unpack_from('<I', data, offset + i * entry_size)[0] == 1]

brand = json.loads((ROOT / 'release/brand.json').read_text())
tool_lock = json.loads((ROOT / 'release/build-tools.json').read_text())
if hashlib.sha256(BUNDLETOOL.read_bytes()).hexdigest() != tool_lock['bundletool']['sha256']:
    raise ValueError('bundletool checksum does not match the pinned release tool')
props = dict(line.split('=', 1) for line in
             (ROOT / '.release-secrets/upload.properties').read_text().splitlines()
             if line and not line.startswith('#'))
validation = bundletool('validate', '--bundle=' + str(BUNDLE))
(DEST / 'bundletool-validation.txt').write_text(validation + '\n')
jar_signature = run([JAVA_HOME / 'bin/jarsigner', '-verify', BUNDLE])
if 'jar verified.' not in jar_signature:
    raise ValueError('The AAB does not have a valid JAR signature')
bundle_certificate = run([JAVA_HOME / 'bin/keytool', '-printcert', '-jarfile', BUNDLE])
bundle_fingerprint = re.search(r'SHA256: ([0-9A-F:]+)', bundle_certificate).group(1).replace(':', '').lower()
apk_set = DEST / 'mtouaa-release.apks'
with tempfile.TemporaryDirectory(prefix='verify-', dir=ROOT / '.release-secrets') as private:
    password_paths = []
    for key in ['storePassword', 'keyPassword']:
        path = Path(private) / key
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(props[key])
        password_paths.append(path)
    bundletool('build-apks', '--bundle=' + str(BUNDLE), '--output=' + str(apk_set),
               '--mode=universal', '--overwrite', '--ks=' + str(ROOT / props['storeFile']),
               '--ks-key-alias=' + props['keyAlias'], '--ks-pass=file:' + str(password_paths[0]),
               '--key-pass=file:' + str(password_paths[1]))
apk = DEST / 'mtouaa-from-bundle.apk'
with zipfile.ZipFile(apk_set) as archive:
    apk.write_bytes(archive.read('universal.apk'))
signature = run([TOOLS / 'apksigner', 'verify', '--print-certs', apk])
apk_fingerprint = re.search(r'certificate SHA-256 digest: (\w+)', signature).group(1)
if bundle_fingerprint != apk_fingerprint:
    raise ValueError('AAB and generated APK do not use the same upload certificate')
run([TOOLS / 'zipalign', '-c', '-P', '16', '4', apk])
badging = run([TOOLS / 'aapt2', 'dump', 'badging', apk])
if "name='" + brand['applicationId'] + "'" not in badging:
    raise ValueError('Wrong public package in AAB')
if 'application-debuggable' in badging:
    raise ValueError('The production bundle is debuggable')
if "targetSdkVersion:'36'" not in badging:
    raise ValueError('Unexpected target SDK')
native = {}
with zipfile.ZipFile(apk) as archive:
    for name in archive.namelist():
        if name.startswith('lib/') and name.endswith('.so'):
            alignments = elf_load_alignments(archive.read(name))
            if not alignments or min(alignments) < 16384:
                raise ValueError('Native library does not support 16 KB pages: ' + name)
            native[name] = alignments
if not native:
    raise ValueError('Native browser runtime is missing')
size_csv = bundletool('get-size', 'total', '--apks=' + str(apk_set))
sizes = [int(n) for n in re.findall(r'\d+', size_csv.splitlines()[-1])]
if not sizes or max(sizes) > 500 * 1024 * 1024:
    raise ValueError('Estimated compressed base download exceeds 500 MB')
report = {
    'bundle': str(BUNDLE.relative_to(ROOT)),
    'bundleSha256': hashlib.sha256(BUNDLE.read_bytes()).hexdigest(),
    'bundletoolValidation': 'PASS',
    'bundleJarSignature': 'PASS',
    'package': brand['applicationId'], 'targetSdk': 36, 'debuggable': False,
    'apkFromBundle': str(apk.relative_to(ROOT)),
    'apkSha256': hashlib.sha256(apk.read_bytes()).hexdigest(),
    'certificateSha256': apk_fingerprint,
    'zipAlignment16KB': 'PASS', 'nativeElfLoadAlignments': native,
    'estimatedCompressedDownloadBytes': max(sizes),
    'sizeEvidence': size_csv,
    'deviceTests': 'Not run by this script; see separate instrumentation results.'
}
(DEST / 'bundle-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['package', 'targetSdk', 'debuggable',
    'zipAlignment16KB', 'estimatedCompressedDownloadBytes']}, indent=2))
print('PASS: signed AAB validated; exact-bundle APK verified; all ' +
      str(len(native)) + ' native libraries support 16 KB page alignment.')
