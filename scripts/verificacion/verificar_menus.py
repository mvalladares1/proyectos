"""Verificar menús creados"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

print("\n=== MENÚS TRASFERENCIAS DASHBOARD ===\n")
menus = odoo.search_read(
    'ir.ui.menu',
    [('name', 'in', ['Trasferencias Dashboard', 'Logs'])],
    ['id', 'name', 'parent_id', 'action', 'sequence']
)

for m in menus:
    print(f"ID: {m['id']}")
    print(f"Nombre: {m['name']}")
    print(f"Parent: {m.get('parent_id', 'Sin padre (menú raíz)')}")
    print(f"Action: {m.get('action', 'Sin action')}")
    print(f"Sequence: {m.get('sequence', 0)}")
    print("-" * 40)
