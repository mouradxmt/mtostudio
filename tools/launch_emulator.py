#!/usr/bin/env python3
"""Open the tablet emulator and an optional suite app, without interrupting other virtual devices."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
SDK = ROOT / '.tools/android-sdk'
ADB = SDK / 'platform-tools/adb'
AVD = 'artcraft-tablet'
PACKAGE = 'org.wordcraft.offline'

def run(*args, timeout=20):
    return subprocess.run([str(ADB), *args], text=True, capture_output=True, timeout=timeout)

def main():
    apps = json.loads((ROOT / 'tools/suite-lock.json').read_text())
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', choices=[app['id'] for app in apps])
    args = parser.parse_args()
    (ROOT / '.tools').mkdir(exist_ok=True)
    with (ROOT / '.tools/emulator-launch.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        listing = run('devices').stdout
        devices = re.findall(r'^(emulator-\d+)\s+(?:device|offline)', listing, re.M)
        serial = None
        for candidate in devices:
            name = run('-s', candidate, 'shell', 'getprop', 'ro.boot.qemu.avd_name', timeout=5).stdout.strip()
            if name == AVD:
                serial = candidate
                break
        if serial is None:
            # The standard tablet port is also reused while that device is still booting.
            if 'emulator-5560' in devices:
                serial = 'emulator-5560'
            else:
                port = next(p for p in range(5560, 5682, 2) if f'emulator-{p}' not in devices)
                serial = f'emulator-{port}'
                env = dict(os.environ, ANDROID_HOME=str(SDK), ANDROID_AVD_HOME=str(ROOT / '.tools/avd'))
                log = (ROOT / '.tools/tablet-emulator.log').open('a')
                subprocess.Popen([str(SDK / 'emulator/emulator'), '-avd', AVD, '-port', str(port),
                    '-gpu', 'host', '-no-snapshot', '-no-skin', '-memory', '4096'],
                    cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
                log.close()
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            boot = run('-s', serial, 'shell', 'getprop', 'sys.boot_completed', timeout=5)
            if boot.stdout.strip() == '1': break
            time.sleep(1)
        else: raise SystemExit('The tablet emulator did not finish booting. See .tools/tablet-emulator.log.')
        name = run('-s', serial, 'shell', 'getprop', 'ro.boot.qemu.avd_name').stdout.strip()
        if name != AVD:
            raise SystemExit('The chosen emulator port belongs to another device; no app was opened.')
        package = run('-s', serial, 'shell', 'dumpsys', 'package', PACKAGE).stdout
        version = re.search(r'versionCode=(\d+)', package)
        if version is None or int(version.group(1)) < 4:
            candidates = [ROOT / 'dist/ArtCraft-Offline-0.3.1-Huawei-arm64-debug.apk',
                          ROOT / 'app/build/outputs/apk/debug/app-debug.apk']
            apk = next((file for file in candidates if file.is_file()), None)
            if apk is None: raise SystemExit('Build the APK with ./tools/build.sh first.')
            result = run('-s', serial, 'install', '--no-incremental', '-r', str(apk), timeout=180)
            if result.returncode != 0: raise SystemExit(result.stdout + result.stderr)
        app = next((app for app in apps if app['id'] == args.app), None)
        alias = ''.join(char for char in app['name'] if char.isalnum()) if app else 'MainActivity'
        result = run('-s', serial, 'shell', 'am', 'start', '-n', PACKAGE + '/.' + alias)
        if result.returncode != 0: raise SystemExit(result.stdout + result.stderr)
        print('Opened ' + (app['name'] if app else 'ArtCraft Offline') + ' in ' + serial)

if __name__ == '__main__': main()
