"""Crear permisos de acceso para el modelo"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

print("\n=== CONFIGURANDO PERMISOS DE ACCESO ===\n")

# 1. Buscar el modelo
models = odoo.search_read("ir.model", [("model", "=", "x_trasferencias_dashboard_v2")], ["id"])
if not models:
    print("✗ Modelo no encontrado")
    exit(1)

model_id = models[0]["id"]
print(f"✓ Modelo ID: {model_id}")

# 2. Buscar grupo base de usuarios
print("\n2. Buscando grupo de usuarios...")
group = odoo.search_read("res.groups", [("name", "=", "User types / Internal User")], ["id"])
if not group:
    # Probar con otro nombre
    group = odoo.search_read("res.groups", [("name", "=", "Internal User")], ["id"])
if not group:
    # Usar grupo base
    group = odoo.search_read("res.groups", [("name", "=", "Employee")], ["id"])

if group:
    group_id = group[0]["id"]
    print(f"   ✓ Grupo encontrado (ID: {group_id})")
else:
    group_id = False
    print("   - Usando sin grupo (acceso total)")

# 3. Crear regla de acceso
print("\n3. Creando regla de acceso...")
try:
    access_id = odoo.execute("ir.model.access", "create", {
        "name": "access_trasferencias_dashboard_v2_all",
        "model_id": model_id,
        "group_id": group_id,
        "perm_read": True,
        "perm_write": True,
        "perm_create": True,
        "perm_unlink": True
    })
    print(f"   ✓ Regla de acceso creada (ID: {access_id})")
except Exception as e:
    if "must be unique" in str(e).lower():
        print("   - Regla ya existe")
    else:
        print(f"   ⚠ Error: {e}")

# 4. Verificar que el action existe
print("\n4. Verificando action...")
actions = odoo.search_read("ir.actions.act_window", [("res_model", "=", "x_trasferencias_dashboard_v2")], ["id", "name"])
if actions:
    print(f"   ✓ Action encontrado: {actions[0]['name']} (ID: {actions[0]['id']})")
    action_id = actions[0]['id']
else:
    print("   ✗ No hay action")
    exit(1)

# 5. Verificar menú
print("\n5. Verificando menú...")
menus = odoo.search_read("ir.ui.menu", [("action", "like", f"ir.actions.act_window,{action_id}")], ["id", "name", "parent_id"])
if menus:
    for menu in menus:
        print(f"   ✓ Menú: {menu['name']} (ID: {menu['id']}, Parent: {menu['parent_id']})")
else:
    print("   ✗ No hay menú vinculado")

print("\n" + "=" * 70)
print("✅ PERMISOS CONFIGURADOS")
print("=" * 70)
print("\nAcción: Cierra sesión y vuelve a entrar, o simplemente:")
print("   Ve directamente a: Inventario > Configuración > Trasferencias Dashboard")
print("   O busca en el menú principal con Ctrl+K: 'trasferencias'")
