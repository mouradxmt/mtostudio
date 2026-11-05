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
import tempfile
import urllib.error
import urllib.request
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parents[2]

def download(url, target, checksum):
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest()==checksum: return
    partial=target.with_suffix(target.suffix+'.partial')
    try:
        try:
            with urllib.request.urlopen(url,timeout=120) as source, partial.open('wb') as output: shutil.copyfileobj(source,output)
        except (urllib.error.URLError,TimeoutError):
            # GitHub's browser-download route can time out while the asset API
            # still works. gh follows API redirects without forwarding tokens.
            parsed=urlparse(url); parts=unquote(parsed.path).strip('/').split('/')
            gh=shutil.which('gh') or str(ROOT/'.tools/gh/gh')
            if parsed.hostname!='github.com' or len(parts)!=6 or parts[2:4]!=['releases','download'] or not Path(gh).is_file(): raise
            with tempfile.TemporaryDirectory(dir=target.parent) as folder:
                subprocess.run([gh,'release','download',parts[4],'--repo','/'.join(parts[:2]),'--pattern',parts[5],'--dir',folder],check=True)
                shutil.copyfile(Path(folder)/parts[5],partial)
        if hashlib.sha256(partial.read_bytes()).hexdigest()!=checksum: raise ValueError('Tool archive checksum mismatch')
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--verification-only', action='store_true'); args = parser.parse_args()
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise RuntimeError('The reviewed tool archives require macOS ARM64 (macos-15).')
    lock = json.loads((ROOT/'release/build-tools.json').read_text())
    tools = ROOT/'.tools'; tools.mkdir(exist_ok=True)
    bundle = tools/'bundletool.jar'; pin = lock['bundletool']
    download(f'https://github.com/google/bundletool/releases/download/{pin["version"]}/bundletool-all-{pin["version"]}.jar',bundle,pin['sha256'])
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
    # Invoke the installed tools directly. Runner-provided rustup proxy builds
    # can dispatch differently after copying them into a project-local CARGO_HOME.
    toolchain = tools/'rustup/toolchains'/(version+'-aarch64-apple-darwin')/'bin'
    for name in ('cargo', 'rustc', 'rustdoc'):
        (cargo/name).unlink(missing_ok=True)
        (cargo/name).symlink_to(toolchain/name)
        subprocess.run([str(cargo/name), '--version'], env=env, check=True)
    binaries = tools/'wasm-bin'; binaries.mkdir(exist_ok=True)
    for name, repo, asset in [
        ('trunk', 'trunk-rs/trunk', 'trunk-aarch64-apple-darwin.tar.gz'),
        ('wasm-bindgen', 'wasm-bindgen/wasm-bindgen', f'wasm-bindgen-{lock["wasm-bindgen"]["version"]}-aarch64-apple-darwin.tar.gz')]:
        pin = lock[name]; archive = tools/(name+'-ci.tar.gz')
        tag = ('v' if name == 'trunk' else '') + pin['version']
        url = f'https://github.com/{repo}/releases/download/{tag}/{asset}'
        download(url,archive,pin['sha256'])
        with tarfile.open(archive) as tar:
            member = next(p for p in tar.getmembers() if Path(p.name).name == name and p.isfile())
            with tar.extractfile(member) as source, (binaries/name).open('wb') as output: shutil.copyfileobj(source, output)
        (binaries/name).chmod(0o755)
    # Match the optimizer recorded from Trunk's original build, including its
    # companion dylib. Verify the whole official archive before extracting.
    optimizer=lock['wasm-opt']
    if optimizer['version']!='131': raise ValueError('Review the optimizer archive pin before changing Binaryen')
    archive=tools/'binaryen-ci.tar.gz'
    download('https://github.com/WebAssembly/binaryen/releases/download/version_131/binaryen-version_131-arm64-macos.tar.gz',archive,
             'e441b48dc22163d209b4f05e44dc7210909b01237642b6c9ae48fd710a3ef83e')
    with tarfile.open(archive) as tar:
        for member_name,target in [('binaryen-version_131/bin/wasm-opt',binaries/'wasm-opt'),('binaryen-version_131/lib/libbinaryen.dylib',tools/'lib/libbinaryen.dylib')]:
            member=tar.getmember(member_name)
            if not member.isfile(): raise ValueError('Unexpected optimizer archive member')
            target.parent.mkdir(exist_ok=True)
            with tar.extractfile(member) as source,target.open('wb') as output:shutil.copyfileobj(source,output)
    if hashlib.sha256((binaries/'wasm-opt').read_bytes()).hexdigest()!=optimizer['executableSha256']:raise ValueError('Optimizer executable checksum mismatch')
    (binaries/'wasm-opt').chmod(0o755)
    subprocess.run([str(binaries/'wasm-opt'),'--version'],check=True)

if __name__ == '__main__': main()
