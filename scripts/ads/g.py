"""Tiny Graph v21 helper for Athena ads ops. Usage: python3 g.py GET|POST path [k=v ...]  (values JSON-parsed if possible)"""
import json, os, sys, urllib.request, urllib.parse, urllib.error
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env = dict(l.rstrip('\n').split('=', 1) for l in open(os.path.join(root, '.env')) if '=' in l and not l.startswith('#'))
T, A = env['ATHENA_META_ACCESS_TOKEN'], env['ATHENA_META_AD_ACCOUNT_ID']
def call(method, path, paged=False, **p):
    p = {k: (v if isinstance(v, str) else json.dumps(v)) for k, v in p.items()}
    p['access_token'] = T
    url = f'https://graph.facebook.com/v21.0/{path}'
    try:
        if method == 'GET':
            url += '?' + urllib.parse.urlencode(p); out = []
            while url:
                d = json.load(urllib.request.urlopen(url, timeout=120))
                if not paged or 'data' not in d: return d
                out += d['data']; url = (d.get('paging') or {}).get('next')
            return out
        return json.load(urllib.request.urlopen(urllib.request.Request(url, data=urllib.parse.urlencode(p).encode(), method=method), timeout=120))
    except urllib.error.HTTPError as e:
        return {'error': json.loads(e.read().decode())}
if __name__ == '__main__':
    m, path, *kv = sys.argv[1:]
    p = {}
    for x in kv:
        k, v = x.split('=', 1); p[k] = v
    print(json.dumps(call(m, path.replace('ACT', A), **p), indent=1))
