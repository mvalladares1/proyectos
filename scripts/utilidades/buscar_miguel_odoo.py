"""Buscar usuario Miguel en Odoo"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.odoo_client import OdooClient

client = OdooClient(
    username='mvalladares@riofuturo.cl',
    password='c0766224bec30cac071ffe43a858c9ccbd521ddd',
    url='https://riofuturo.server98c6e.oerpondemand.net',
    db='riofuturo-master'
)

users = client.search_read(
    'res.users',
    [['login', 'ilike', 'miguel']],
    ['id', 'name', 'login']
)

print(f"{'ID':<6} | {'Login':<40} | {'Name'}")
print("-" * 80)
for u in users:
    print(f"{u['id']:<6} | {u['login']:<40} | {u['name']}")
