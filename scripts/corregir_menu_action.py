"""Corregir el menú para que apunte al modelo correcto"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

print("\n=== CORRIGIENDO MENÚ Y ACTION ===\n")

# 1. Ver el action actual del menú 993
print("1. Verificando action actual...")
menu = odoo.search_read('ir.ui.menu', [('id', '=', 993)], ['action'])
if menu and menu[0].get('action'):
    action_str = menu[0]['action']
    action_id = int(action_str.split(',')[1])
    print(f"   Action actual ID: {action_id}")
    
    # Ver a qué modelo apunta
    action_data = odoo.search_read('ir.actions.act_window', [('id', '=', action_id)], ['res_model'])
    print(f"   Modelo actual: {action_data[0]['res_model']}")
    
    # 2. Actualizar el action para que apunte al modelo v2
    print("\n2. Actualizando action al modelo v2...")
    odoo.execute("ir.actions.act_window", "write", [action_id], {
        "res_model": "x_trasferencias_dashboard_v2"
    })
    print("   ✓ Action actualizado")

# 3. Eliminar vistas del modelo viejo
print("\n3. Eliminando vistas del modelo viejo...")
old_views = odoo.search("ir.ui.view", [("model", "=", "x_trasferencias_dashboard")])
if old_views:
    odoo.execute("ir.ui.view", "unlink", old_views)
    print(f"   ✓ {len(old_views)} vistas viejas eliminadas")
else:
    print("   - No hay vistas viejas")

print("\n" + "=" * 60)
print("✅ CORRECCIÓN COMPLETADA")
print("=" * 60)
print("\n⚠️  IMPORTANTE: Refresca el navegador con Ctrl+Shift+R")
print("   (o Ctrl+F5 para forzar recarga completa)")
