"""Hacer visible el menú como aplicación"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

print("\n=== HACIENDO VISIBLE EL MENÚ ===\n")

# 1. Actualizar el menú 993 para que sea una aplicación visible
print("1. Actualizando menú 993...")
odoo.execute("ir.ui.menu", "write", [993], {
    "name": "Trasferencias Dashboard",
    "parent_id": False,
    "sequence": 10,
    "web_icon": "stock,static/description/icon.png"  # Usar ícono de stock
})
print("   ✓ Menú actualizado como aplicación")

# 2. Verificar que el menú esté en la raíz
print("\n2. Verificando menú...")
menu = odoo.search_read('ir.ui.menu', [('id', '=', 993)], ['name', 'parent_id', 'action', 'sequence'])
print(f"   Nombre: {menu[0]['name']}")
print(f"   Parent: {menu[0]['parent_id']}")
print(f"   Action: {menu[0]['action']}")
print(f"   Sequence: {menu[0]['sequence']}")

# 3. Verificar el action
if menu[0].get('action'):
    action_id = int(menu[0]['action'].split(',')[1])
    action = odoo.search_read('ir.actions.act_window', [('id', '=', action_id)], ['name', 'res_model'])
    print(f"\n3. Action del menú:")
    print(f"   Nombre: {action[0]['name']}")
    print(f"   Modelo: {action[0]['res_model']}")

print("\n" + "=" * 60)
print("✅ MENÚ CONFIGURADO")
print("=" * 60)
print("\nPrueba:")
print("1. Refresca el navegador (Ctrl+Shift+R)")
print("2. Busca 'Trasferencias Dashboard' en la pantalla principal")
print("   (puede estar al final de la lista de aplicaciones)")
