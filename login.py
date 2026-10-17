#!/usr/bin/env python3
"""
Mistral Le Chat login via Ory Kratos (scripted, no browser needed).

Usage:
    MISTRAL_EMAIL=you@example.com python3 login.py
    # enter password via stdin (not logged, not stored)

    # or: MISTRAL_EMAIL=you@example.com MISTRAL_PW=xxx python3 login.py

Saves the session cookie to data/session.json (chmod 0600).
The session lasts ~3 months; re-run when the gateway returns 401.
"""
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse

EMAIL = os.environ.get('MISTRAL_EMAIL', '').strip()
PW = os.environ.get('MISTRAL_PW', '').strip()
if not PW and not sys.stdin.isatty():
    PW = sys.stdin.readline().strip()
if not EMAIL or not PW:
    print('Usage: MISTRAL_EMAIL=you@example.com [MISTRAL_PW=xxx] python3 login.py',
          file=sys.stderr)
    sys.exit(1)

PROXY = os.environ.get('https_proxy') or os.environ.get('HTTPS_PROXY')

jar = tempfile.mktemp(prefix='kjar-', suffix='.txt')
open(jar, 'w').close()
os.chmod(jar, 0o600)


def curl(url, data_dict=None, extra_headers=None):
    cmd = ['curl', '-s', '-x', PROXY, '--max-time', '30',
           '-b', jar, '-c', jar, '-D', '-', '-o', '/tmp/kbody.tmp', url]
    if extra_headers:
        for h in extra_headers:
            cmd += ['-H', h]
    datafile = None
    if data_dict:
        datafile = tempfile.mktemp(prefix='kdata-')
        with open(datafile, 'w') as f:
            f.write(urllib.parse.urlencode(data_dict))
        os.chmod(datafile, 0o600)
        cmd += ['--data', '@' + datafile]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        headers = r.stdout
        body = open('/tmp/kbody.tmp').read()
        code = [l for l in headers.split('\n') if l.startswith('HTTP/')][-1].split()[1]
        return int(code), headers, body
    finally:
        if datafile and os.path.exists(datafile):
            os.remove(datafile)


# 1. Create login flow
code, hdrs, _ = curl('https://auth.mistral.ai/self-service/login/browser?return_to=' +
                     urllib.parse.quote('https://chat.mistral.ai', safe=''))
loc = [l.split(':', 1)[1].strip() for l in hdrs.split('\n')
       if l.lower().startswith('location:')][0]
fid = loc.split('flow=')[1].split('&')[0]

# 2. Get csrf_token
code, _, body = curl(f'https://auth.mistral.ai/self-service/login/flows?id={fid}',
                     extra_headers=['Accept: application/json'])
d = json.loads(body)
csrf = next(n['attributes']['value'] for n in d['ui']['nodes']
            if n['attributes'].get('name') == 'csrf_token')
action = d['ui']['action']

# 3. identifier_first -> choose_method
code, _, body = curl(action,
                     {'identifier': EMAIL, 'method': 'identifier_first',
                      'csrf_token': csrf},
                     ['Accept: application/json'])
d = json.loads(body)
csrf = next(n['attributes']['value'] for n in d['ui']['nodes']
            if n['attributes'].get('name') == 'csrf_token')
action = d['ui']['action']

# 4. Password login (browser mode: no Accept:json -> 303 + session cookie)
code, hdrs, body = curl(action,
                        {'identifier': EMAIL, 'password': PW,
                         'method': 'password', 'csrf_token': csrf})
if code not in (303, 302):
    print(f'Login failed (HTTP {code}): {body[:300]}', file=sys.stderr)
    sys.exit(1)

# Extract session cookie manually from Set-Cookie (curl's jar drops them)
cookies = {}
for l in hdrs.split('\n'):
    if l.lower().startswith('set-cookie:'):
        pair = l.split(':', 1)[1].strip().split(';')[0]
        if '=' in pair:
            n, v = pair.split('=', 1)
            n = n.strip()
            if n not in ('__cf_bm', '__cflb', '_cfuvid') and 'csrf_token' not in n:
                cookies[n] = v.strip()
if not cookies:
    print('No session cookie found', file=sys.stderr)
    sys.exit(1)

os.makedirs('data', exist_ok=True)
out = {'_meta': {'email': EMAIL, 'obtained_at': 'manual'},
       'cookies': {n: {'value': v, 'domain': '.mistral.ai'}
                   for n, v in cookies.items()}}
with open('data/session.json', 'w') as f:
    json.dump(out, f)
os.chmod('data/session.json', 0o600)
os.remove(jar)
print(f'OK: session saved ({len(cookies)} cookie(s)) -> data/session.json')
