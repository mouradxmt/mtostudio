#!/usr/bin/env python3
"""Retry transient transport failures; never relax source, checksum or license gates."""
from collections import deque
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
NETWORK = ('HTTP Error 502', 'HTTP Error 503', 'HTTP Error 504', 'Gateway Timeout', 'Gateway Time-out',
           'HTTP 502', 'HTTP 503', 'HTTP 504',
           'response code: 502', 'response code: 503', 'response code: 504', 'TLS handshake timeout',
           'Client(502)', 'Client(503)', 'Client(504)', 'failed downloading release archive',
           'Connection reset', 'Connection timed out', 'timed out', 'Temporary failure in name resolution')

def retry(command, invoke, sleep=time.sleep):
    for attempt in range(3):
        code, details = invoke(command)
        if code == 0: return 0
        if attempt == 2 or not any(reason in details for reason in NETWORK): return code
        print('Transient download failure; retrying the same reviewed inputs ('+str(attempt+2)+'/3).', flush=True)
        sleep(10 * (attempt+1))
    raise AssertionError('Unreachable')

def invoke(command):
    started = time.time(); tail = deque(maxlen=200)
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace') as process:
        for line in process.stdout:
            sys.stdout.write(line); sys.stdout.flush(); tail.append(line)
        code = process.wait()
    details = ''.join(tail)
    for path in (ROOT/'.tools/play-logs').glob('*.log'):
        if path.stat().st_mtime >= started:
            with path.open('rb') as source:
                source.seek(max(0,path.stat().st_size-32768)); details += source.read().decode(errors='replace')
    return code, details

if __name__ == '__main__':
    if len(sys.argv)<2: raise SystemExit('Usage: retry.py COMMAND [ARGS]')
    raise SystemExit(retry(sys.argv[1:], invoke))
