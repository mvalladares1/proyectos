"""Discover base.automation fields"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from xmlrpc import client as xmlrpc_client

url = "https://riofuturo.server98c6e.oerpondemand.net"
db = "riofuturo-master"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

common = xmlrpc_client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc_client.ServerProxy(f'{url}/xmlrpc/2/object')

fields = models.execute_kw(db, uid, password, 'base.automation', 'fields_get', [], 
    {'attributes': ['string', 'type', 'relation', 'selection']})

for k, v in sorted(fields.items()):
    sel = f" sel={v['selection']}" if v.get('selection') else ""
    rel = f" rel={v['relation']}" if v.get('relation') else ""
    print(f"  {k}: {v['type']} | {v['string']}{rel}{sel}")

# Also check existing automations to see structure
print("\n\nExisting automations (first 3):")
existing = models.execute_kw(db, uid, password, 'base.automation', 'search_read', 
    [[]], {'fields': list(fields.keys()), 'limit': 3})
for e in existing:
    print(f"\n  ID={e['id']} | {e.get('name','?')}")
    for k, v in e.items():
        if v and k not in ('id',):
            print(f"    {k} = {str(v)[:150]}")

# Also check x_studio_titulo_control_calidad values
print("\n\nValores unicos de x_studio_titulo_control_calidad:")
qcs = models.execute_kw(db, uid, password, 'quality.check', 'read_group', 
    [[], ['x_studio_titulo_control_calidad'], ['x_studio_titulo_control_calidad']], 
    {'limit': 50})
for q in qcs:
    print(f"  '{q.get('x_studio_titulo_control_calidad', '?')}' -> {q.get('x_studio_titulo_control_calidad_count', '?')} registros")
