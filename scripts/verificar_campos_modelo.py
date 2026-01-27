"""Script para verificar campos del modelo"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

print("\n=== CAMPOS EN EL MODELO x_trasferencias_dashboard ===\n")
fields = odoo.execute('x_trasferencias_dashboard', 'fields_get')
for k, v in fields.items():
    if k.startswith('x_'):
        print(f"{k}: {v.get('string')} ({v.get('type')})")
