"""
Script para eliminar menús duplicados de "Trasferencias Dashboard" y "Logs"
Mantiene solo uno de cada tipo y elimina los demás

Uso:
    python scripts/limpiar_menus_duplicados.py
"""

import sys
import os

# Agregar el directorio raíz al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

# Credenciales
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

def main():
    """Elimina menús duplicados."""
    
    print("=" * 80)
    print("LIMPIEZA DE MENÚS DUPLICADOS")
    print("=" * 80)
    
    # Conectar a Odoo
    print("\n1. Conectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("   ✓ Conectado exitosamente")
    
    # Buscar todos los menús que contengan "trasferencia", "transferencia" o "logs"
    print("\n2. Buscando menús...")
    menus = odoo.search_read(
        "ir.ui.menu",
        [
            "|", "|",
            ("name", "ilike", "trasferencia"),
            ("name", "ilike", "transferencia"),
            ("name", "=", "Logs")
        ],
        ["id", "name", "action", "create_date", "parent_id"],
        order="create_date desc"
    )
    
    if not menus:
        print("   ⚠ No se encontraron menús")
        return
    
    print(f"   ✓ Encontrados {len(menus)} menús:")
    for idx, m in enumerate(menus):
        action_info = m.get('action', 'Sin acción')
        parent = m.get('parent_id', False)
        parent_info = f" (Padre: {parent[1]})" if parent else ""
        print(f"     {idx + 1}. {m['name']} (ID: {m['id']}){parent_info}")
    
    if len(menus) <= 1:
        print("\n   ✓ Solo hay un menú o ninguno, no hay duplicados que eliminar")
        return
    
    # Agrupar por nombre
    grupos = {}
    for m in menus:
        nombre = m['name']
        if nombre not in grupos:
            grupos[nombre] = []
        grupos[nombre].append(m)
    
    print(f"\n3. Procesando duplicados por grupo...")
    total_eliminados = 0
    
    for nombre, grupo in grupos.items():
        if len(grupo) <= 1:
            continue
        
        print(f"\n   Grupo '{nombre}': {len(grupo)} menús")
        
        # Mantener el primero (más reciente)
        menu_mantener = grupo[0]
        menus_eliminar = grupo[1:]
        
        print(f"     ✓ Manteniendo: ID {menu_mantener['id']}")
        
        for m in menus_eliminar:
            try:
                odoo.execute("ir.ui.menu", "unlink", [m['id']])
                print(f"     ✓ Eliminado: ID {m['id']}")
                total_eliminados += 1
            except Exception as e:
                print(f"     ✗ Error eliminando ID {m['id']}: {e}")
    
    print("\n" + "=" * 80)
    print("LIMPIEZA COMPLETADA")
    print("=" * 80)
    print(f"\nRESUMEN:")
    print(f"  - Total menús eliminados: {total_eliminados}")
    print(f"\n✅ Duplicados eliminados")
    print(f"\nNOTA: Refresca el navegador (F5) para ver los cambios")


if __name__ == "__main__":
    main()
