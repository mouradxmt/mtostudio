#!/usr/bin/env python3
"""Install the pinned source-build tools on a macOS ARM64 GitHub runner."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--verification-only', action='store_true'); args = parser.parse_args()
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise RuntimeError('The reviewed tool archives require macOS ARM64 (macos-15).')
    lock = json.loads((ROOT/'release/build-tools.json').read_text())
    tools = ROOT/'.tools'; tools.mkdir(exist_ok=True)
    bundle = tools/'bundletool.jar'; pin = lock['bundletool']
    if not bundle.exists():
        with urllib.request.urlopen(f'https://github.com/google/bundletool/releases/download/{pin["version"]}/bundletool-all-{pin["version"]}.jar', timeout=120) as source, bundle.open('wb') as output: shutil.copyfileobj(source, output)
    if hashlib.sha256(bundle.read_bytes()).hexdigest() != pin['sha256']: raise ValueError('bundletool checksum mismatch')
    if args.verification_only: return
    cargo = tools/'cargo/bin'; cargo.mkdir(parents=True, exist_ok=True)
    rustup = shutil.which('rustup')
    if not rustup: raise RuntimeError('The GitHub runner must supply rustup.')
    if not (cargo/'rustup').exists(): shutil.copy2(rustup, cargo/'rustup')
    for name in ('cargo', 'rustc', 'rustdoc'):
        if not (cargo/name).exists(): (cargo/name).symlink_to('rustup')
    env = dict(os.environ, RUSTUP_HOME=str(tools/'rustup'), CARGO_HOME=str(tools/'cargo'))
    version = lock['rust'].split()[0]
    subprocess.run([str(cargo/'rustup'), 'toolchain', 'install', version, '--profile', 'minimal', '--target', lock['target']], env=env, check=True)
    subprocess.run([str(cargo/'rustup'), 'default', version], env=env, check=True)
    binaries = tools/'wasm-bin'; binaries.mkdir(exist_ok=True)
    for name, repo, asset in [
        ('trunk', 'trunk-rs/trunk', 'trunk-aarch64-apple-darwin.tar.gz'),
        ('wasm-bindgen', 'wasm-bindgen/wasm-bindgen', f'wasm-bindgen-{lock["wasm-bindgen"]["version"]}-aarch64-apple-darwin.tar.gz')]:
        pin = lock[name]; archive = tools/(name+'-ci.tar.gz')
        tag = ('v' if name == 'trunk' else '') + pin['version']
        url = f'https://github.com/{repo}/releases/download/{tag}/{asset}'
        if not archive.exists():
            with urllib.request.urlopen(url, timeout=120) as source, archive.open('wb') as output: shutil.copyfileobj(source, output)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != pin['sha256']: raise ValueError('Tool archive checksum mismatch: '+name)
        with tarfile.open(archive) as tar:
            member = next(p for p in tar.getmembers() if Path(p.name).name == name and p.isfile())
            with tar.extractfile(member) as source, (binaries/name).open('wb') as output: shutil.copyfileobj(source, output)
        (binaries/name).chmod(0o755)

if __name__ == '__main__': main()
