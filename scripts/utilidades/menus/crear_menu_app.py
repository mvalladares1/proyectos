"""Crear menú desde cero como aplicación visible"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

print("\n=== CREANDO MENÚ TRASFERENCIAS DASHBOARD ===\n")

# 1. Verificar/Crear action para el modelo v2
print("1. Creando action para el modelo...")
action_id = odoo.execute("ir.actions.act_window", "create", {
    "name": "Trasferencias Dashboard",
    "res_model": "x_trasferencias_dashboard_v2",
    "view_mode": "tree,form",
    "target": "current"
})
print(f"   ✓ Action creado (ID: {action_id})")

# 2. Crear menú raíz (aplicación)
print("\n2. Creando menú de aplicación...")
menu_id = odoo.execute("ir.ui.menu", "create", {
    "name": "Trasferencias Dashboard",
    "action": f"ir.actions.act_window,{action_id}",
    "parent_id": False,
    "sequence": 10,
    "web_icon": "stock,static/description/icon.png"
})
print(f"   ✓ Menú creado (ID: {menu_id})")

# 3. Verificar modelo
print("\n3. Verificando modelo x_trasferencias_dashboard_v2...")
try:
    fields = odoo.execute('x_trasferencias_dashboard_v2', 'fields_get')
    x_fields = [k for k in fields.keys() if k.startswith('x_')]
    print(f"   ✓ Modelo existe con {len(x_fields)} campos custom")
    for f in x_fields:
        print(f"      - {f}: {fields[f].get('string')}")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 70)
print("✅ MENÚ CREADO EXITOSAMENTE")
print("=" * 70)
print(f"\nID del menú: {menu_id}")
print(f"ID del action: {action_id}")
print("\n⚠️  IMPORTANTE:")
print("   1. Refresca el navegador con Ctrl+Shift+R")
print("   2. Busca 'Trasferencias Dashboard' en la pantalla de aplicaciones")
print("   3. Puede aparecer al final de la lista")
