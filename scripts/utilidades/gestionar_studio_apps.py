"""
Script para buscar y eliminar apps creadas con Studio
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.odoo_client import OdooClient

# Credenciales
ODOO_URL = "https://riofuturo.server98c6e.oerpondemand.net"
ODOO_DB = "riofuturo-master"
ODOO_USER = "mvalladares@riofuturo.cl"
ODOO_PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"


def list_studio_apps():
    """Listar aplicaciones creadas con Studio"""
    client = OdooClient(
        username=ODOO_USER,
        password=ODOO_PASSWORD,
        url=ODOO_URL,
        db=ODOO_DB
    )
    
    print("=" * 70)
    print("🔍 BUSCANDO MENÚS 'LOGS'")
    print("=" * 70)
    
    # Buscar menús con "log" en el nombre
    log_menus = client.search_read(
        'ir.ui.menu',
        [['name', 'ilike', 'log']],
        ['id', 'name', 'parent_id', 'action', 'web_icon', 'complete_name']
    )
    
    for m in log_menus:
        print(f"\n  ID: {m['id']}")
        print(f"  Nombre: {m['name']}")
        print(f"  Ruta completa: {m.get('complete_name')}")
        print(f"  Parent: {m.get('parent_id')}")
        print(f"  Action: {m.get('action')}")
    
    print("\n" + "=" * 70)
    print("🔍 BUSCANDO MENÚS DE PRIMER NIVEL (Apps principales)")
    print("=" * 70)
    
    # Buscar menús raíz (sin parent) - son las apps principales
    root_menus = client.search_read(
        'ir.ui.menu',
        [['parent_id', '=', False]],
        ['id', 'name', 'action', 'web_icon', 'sequence'],
        order='sequence'
    )
    
    for m in root_menus:
        print(f"  [{m['id']:4d}] {m['name']:<30} | Icon: {m.get('web_icon', '-')[:30] if m.get('web_icon') else '-'}")
    
    print("\n" + "=" * 70)
    print("🔍 BUSCANDO MENÚS 'Transferencia' o similares")
    print("=" * 70)
    
    transfer_menus = client.search_read(
        'ir.ui.menu',
        ['|', '|', ['name', 'ilike', 'transferencia'], ['name', 'ilike', 'transfer'], ['name', 'ilike', 'dashboard']],
        ['id', 'name', 'parent_id', 'complete_name', 'action']
    )
    
    # Filtrar solo los de primer nivel o segundo nivel
    for m in transfer_menus:
        parent = m.get('parent_id')
        if not parent or (parent and not '/' in str(m.get('complete_name', ''))):
            print(f"\n  ID: {m['id']}")
            print(f"  Nombre: {m['name']}")
            print(f"  Ruta: {m.get('complete_name')}")
            print(f"  Action: {m.get('action')}")


def delete_menu(menu_id: int, dry_run: bool = True):
    """Eliminar un menú y sus submenús"""
    client = OdooClient(
        username=ODOO_USER,
        password=ODOO_PASSWORD,
        url=ODOO_URL,
        db=ODOO_DB
    )
    
    # Buscar info del menú
    menu = client.search_read(
        'ir.ui.menu',
        [['id', '=', menu_id]],
        ['id', 'name', 'complete_name', 'action', 'child_id']
    )
    
    if not menu:
        print(f"❌ Menú {menu_id} no encontrado")
        return
    
    menu = menu[0]
    print(f"\n{'='*60}")
    print(f"🗑️ {'[DRY RUN] ' if dry_run else ''}Eliminando menú:")
    print(f"   ID: {menu['id']}")
    print(f"   Nombre: {menu['name']}")
    print(f"   Ruta: {menu.get('complete_name')}")
    
    # Buscar submenús
    child_menus = client.search_read(
        'ir.ui.menu',
        [['parent_id', '=', menu_id]],
        ['id', 'name']
    )
    
    if child_menus:
        print(f"\n   ⚠️ Este menú tiene {len(child_menus)} submenús que también se eliminarán:")
        for c in child_menus:
            print(f"      - [{c['id']}] {c['name']}")
    
    if dry_run:
        print(f"\n   ℹ️ Ejecuta con dry_run=False para eliminar realmente")
    else:
        # Eliminar el menú (los hijos se eliminan en cascada)
        try:
            client.models.execute_kw(
                client.db, client.uid, client.password,
                'ir.ui.menu', 'unlink', [[menu_id]]
            )
            print(f"\n   ✅ Menú eliminado correctamente")
        except Exception as e:
            print(f"\n   ❌ Error eliminando: {e}")


if __name__ == "__main__":
    # Eliminar menús duplicados - conservar solo 997
    menus_to_delete = [996, 995, 993]  # Primero el hijo, luego los padres
    
    for menu_id in menus_to_delete:
        delete_menu(menu_id, dry_run=False)
    
    print("\n🎉 Limpieza completada. Solo queda el menú 997 (Trasferencias Dashboard)")
