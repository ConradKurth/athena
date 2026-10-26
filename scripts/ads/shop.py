"""Shopify Admin GraphQL access for the ads scripts.

Mints a 24h token with the client-credentials grant from .env SHOPIFY_CLIENT_ID / SHOPIFY_CLIENT_SECRET,
so no `make auth` login is needed. Falls back to the shopify-admin OAuth session in .home/ if present.
"""
import json, os, urllib.request, urllib.parse
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env = dict(l.rstrip('\n').split('=', 1) for l in open(os.path.join(root, '.env')) if '=' in l and not l.startswith('#'))
_tok = None

def token():
    global _tok
    if _tok: return _tok
    store, cid, secret = env.get('MYSHOPIFY_DOMAIN'), env.get('SHOPIFY_CLIENT_ID'), env.get('SHOPIFY_CLIENT_SECRET')
    if store and cid and secret:
        body = urllib.parse.urlencode({'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': secret}).encode()
        d = json.load(urllib.request.urlopen(urllib.request.Request(f'https://{store}/admin/oauth/access_token', data=body), timeout=30))
        _tok = {'store': store, 'access_token': d['access_token']}
    else:
        _tok = json.load(open(os.path.join(root, '.home/Library/Application Support/shopify-admin/token.json')))
    return _tok

def gql(q, v=None, timeout=60):
    t = token()
    req = urllib.request.Request(f"https://{t['store']}/admin/api/2025-10/graphql.json",
                                 data=json.dumps({'query': q, 'variables': v or {}}).encode(),
                                 headers={'Content-Type': 'application/json', 'X-Shopify-Access-Token': t['access_token']})
    d = json.load(urllib.request.urlopen(req, timeout=timeout))
    if 'errors' in d: raise SystemExit(json.dumps(d['errors'])[:800])
    return d['data']
