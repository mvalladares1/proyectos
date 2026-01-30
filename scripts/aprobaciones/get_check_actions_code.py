"""
Ver el código completo de las acciones Check 1 y Check 2
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("Conectando...")
odoo = OdooClient(username=USERNAME, password=PASSWORD)
print("OK\n")

# Leer las acciones 1015 y 1016
actions = odoo.search_read(
    'ir.actions.server',
    [['id', 'in', [1015, 1016]]],
    ['id', 'name', 'code', 'state'],
    limit=10
)

for action in actions:
    print("=" * 100)
    print(f"ACCION: {action.get('name', '')} (ID: {action['id']})")
    print("=" * 100)
    print(f"Tipo: {action.get('state', '')}")
    
    if action.get('code'):
        print(f"\nCodigo Python:")
        print("-" * 100)
        print(action.get('code', ''))
        print("-" * 100)
    
    if action.get('fields_lines'):
        print(f"\nFields lines: {action.get('fields_lines')}")
    
    if action.get('update_field_id'):
        print(f"\nUpdate field: {action.get('update_field_id')}")
    
    if action.get('update_path'):
        print(f"Update path: {action.get('update_path')}")
    
    if action.get('value'):
        print(f"Value: {action.get('value')}")
    
    print("\n")

print("=" * 100)
print("DONE")
print("=" * 100)
