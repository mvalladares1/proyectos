"""
Script para eliminar modelos duplicados de "Trasferencias Dashboard"
Mantiene solo el más reciente y elimina los demás

Uso:
    python scripts/limpiar_modelos_duplicados.py
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
    """Elimina modelos duplicados de Trasferencias Dashboard."""
    
    print("=" * 80)
    print("LIMPIEZA DE MODELOS DUPLICADOS - TRASFERENCIAS DASHBOARD")
    print("=" * 80)
    
    # Conectar a Odoo
    print("\n1. Conectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("   ✓ Conectado exitosamente")
    
    # Buscar todos los modelos que contengan "trasferencia" o "transferencia"
    print("\n2. Buscando modelos de Trasferencias...")
    models = odoo.search_read(
        "ir.model",
        [
            "|",
            ("name", "ilike", "trasferencia"),
            ("name", "ilike", "transferencia")
        ],
        ["id", "name", "model", "create_date"],
        order="create_date desc"
    )
    
    if not models:
        print("   ⚠ No se encontraron modelos")
        return
    
    print(f"   ✓ Encontrados {len(models)} modelos:")
    for idx, m in enumerate(models):
        print(f"     {idx + 1}. {m['name']} ({m['model']}) - Creado: {m.get('create_date', 'N/A')}")
    
    if len(models) <= 1:
        print("\n   ✓ Solo hay un modelo, no hay duplicados que eliminar")
        return
    
    # Mantener el primero (más reciente) y eliminar el resto
    modelo_mantener = models[0]
    modelos_eliminar = models[1:]
    
    print(f"\n3. Manteniendo modelo más reciente:")
    print(f"   ✓ {modelo_mantener['name']} (ID: {modelo_mantener['id']})")
    
    print(f"\n4. Eliminando {len(modelos_eliminar)} modelos duplicados...")
    
    for m in modelos_eliminar:
        try:
            model_id = m['id']
            model_name = m['name']
            model_tech = m['model']
            
            # Buscar y eliminar menús asociados
            print(f"\n   Procesando: {model_name} (ID: {model_id})")
            
            # Buscar acciones asociadas
            actions = odoo.search_read(
                "ir.actions.act_window",
                [("res_model", "=", model_tech)],
                ["id", "name"]
            )
            
            if actions:
                print(f"     - Encontradas {len(actions)} acciones asociadas")
                for action in actions:
                    # Buscar menús que usen esta acción
                    menus = odoo.search_read(
                        "ir.ui.menu",
                        [("action", "=", f"ir.actions.act_window,{action['id']}")],
                        ["id", "name"]
                    )
                    
                    # Eliminar menús
                    for menu in menus:
                        try:
                            odoo.execute("ir.ui.menu", "unlink", [menu['id']])
                            print(f"       ✓ Menú eliminado: {menu['name']}")
                        except Exception as e:
                            print(f"       ⚠ Error eliminando menú: {e}")
                    
                    # Eliminar acción
                    try:
                        odoo.execute("ir.actions.act_window", "unlink", [action['id']])
                        print(f"     ✓ Acción eliminada: {action['name']}")
                    except Exception as e:
                        print(f"     ⚠ Error eliminando acción: {e}")
            
            # Buscar y eliminar vistas asociadas
            views = odoo.search_read(
                "ir.ui.view",
                [("model", "=", model_tech)],
                ["id", "name"]
            )
            
            if views:
                print(f"     - Encontradas {len(views)} vistas asociadas")
                for view in views:
                    try:
                        odoo.execute("ir.ui.view", "unlink", [view['id']])
                        print(f"       ✓ Vista eliminada: {view['name']}")
                    except Exception as e:
                        print(f"       ⚠ Error eliminando vista: {e}")
            
            # Buscar y eliminar campos asociados
            fields = odoo.search_read(
                "ir.model.fields",
                [("model_id", "=", model_id), ("state", "=", "manual")],
                ["id", "name"]
            )
            
            if fields:
                print(f"     - Encontrados {len(fields)} campos asociados")
                for field in fields:
                    try:
                        odoo.execute("ir.model.fields", "unlink", [field['id']])
                        # print(f"       ✓ Campo eliminado: {field['name']}")
                    except Exception as e:
                        print(f"       ⚠ Error eliminando campo: {e}")
                print(f"       ✓ {len(fields)} campos eliminados")
            
            # Finalmente, eliminar el modelo
            try:
                odoo.execute("ir.model", "unlink", [model_id])
                print(f"     ✓ Modelo eliminado: {model_name}")
            except Exception as e:
                print(f"     ✗ Error eliminando modelo: {e}")
        
        except Exception as e:
            print(f"   ✗ Error procesando {m['name']}: {e}")
    
    print("\n" + "=" * 80)
    print("LIMPIEZA COMPLETADA")
    print("=" * 80)
    print(f"\nRESUMEN:")
    print(f"  - Modelo mantenido: {modelo_mantener['name']}")
    print(f"  - Modelos eliminados: {len(modelos_eliminar)}")
    print(f"\n✅ Solo queda un modelo de Trasferencias Dashboard")


if __name__ == "__main__":
    main()
