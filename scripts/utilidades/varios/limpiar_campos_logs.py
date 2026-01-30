"""
Script para limpiar campos viejos y configurar correctamente el modelo

Uso:
    python scripts/limpiar_campos_logs.py
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
    """Limpia campos viejos y configura correctamente."""
    
    print("=" * 80)
    print("LIMPIEZA Y CONFIGURACIÓN DE TRASFERENCIAS DASHBOARD")
    print("=" * 80)
    
    # Conectar a Odoo
    print("\n1. Conectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("   ✓ Conectado exitosamente")
    
    # Buscar el modelo
    print("\n2. Buscando modelo...")
    models = odoo.search_read(
        "ir.model",
        [("model", "=", "x_trasferencias_dashboard")],
        ["id", "name"]
    )
    
    if not models:
        print("   ✗ ERROR: Modelo no encontrado")
        return
    
    model_id = models[0]["id"]
    print(f"   ✓ Modelo encontrado (ID: {model_id})")
    
    # Obtener todos los campos actuales
    print("\n3. Obteniendo campos actuales...")
    all_fields = odoo.search_read(
        "ir.model.fields",
        [("model_id", "=", model_id), ("state", "=", "manual")],
        ["id", "name", "field_description", "ttype"]
    )
    
    print(f"   ✓ Campos actuales: {len(all_fields)}")
    for f in all_fields:
        print(f"     - {f['name']}: {f['field_description']}")
    
    # Campos viejos a eliminar
    campos_viejos = [
        'x_studio_responsable',
        'x_studio_new_html',
        'x_studio_pedido_de_compra',
        'x_studio_contacto',
        'x_studio_telfono',
        'x_studio_correo_electrnico',
        'x_studio_fecha'
    ]
    
    print("\n4. Eliminando campos viejos...")
    eliminados = 0
    for field in all_fields:
        if field['name'] in campos_viejos:
            try:
                odoo.execute("ir.model.fields", "unlink", [field['id']])
                print(f"   ✓ Eliminado: {field['field_description']}")
                eliminados += 1
            except Exception as e:
                print(f"   ⚠ Error eliminando {field['name']}: {e}")
    
    print(f"\n   Total eliminados: {eliminados}")
    
    # Verificar campos correctos
    print("\n5. Verificando campos correctos...")
    campos_correctos = [
        'x_name',
        'x_fecha_hora',
        'x_paquete_id',
        'x_ubicacion_origen_id',
        'x_ubicacion_destino_id',
        'x_usuario_id',
        'x_total_kg',
        'x_cantidad_quants',
        'x_detalles',
        'x_estado',
        'x_origen_sistema'
    ]
    
    campos_existentes = [f['name'] for f in all_fields if f['name'] not in campos_viejos]
    campos_faltantes = [c for c in campos_correctos if c not in campos_existentes]
    
    if campos_faltantes:
        print(f"   ⚠ Faltan {len(campos_faltantes)} campos:")
        for c in campos_faltantes:
            print(f"     - {c}")
    else:
        print("   ✓ Todos los campos correctos están presentes")
    
    # Eliminar vistas viejas
    print("\n6. Eliminando vistas viejas...")
    views = odoo.search_read(
        "ir.ui.view",
        [("model", "=", "x_trasferencias_dashboard")],
        ["id", "name", "type"]
    )
    
    for view in views:
        try:
            odoo.execute("ir.ui.view", "unlink", [view['id']])
            print(f"   ✓ Vista eliminada: {view['name']}")
        except Exception as e:
            print(f"   ⚠ Error: {e}")
    
    # Crear vistas nuevas correctas
    print("\n7. Creando vistas correctas...")
    
    # Vista lista
    vista_tree = """<?xml version="1.0"?>
<tree string="Trasferencias Dashboard">
    <field name="x_name"/>
    <field name="x_fecha_hora"/>
    <field name="x_ubicacion_origen_id"/>
    <field name="x_ubicacion_destino_id"/>
    <field name="x_total_kg"/>
    <field name="x_estado"/>
</tree>"""
    
    try:
        odoo.execute("ir.ui.view", "create", {
            "name": "x_trasferencias_dashboard.tree",
            "model": "x_trasferencias_dashboard",
            "type": "tree",
            "arch": vista_tree
        })
        print("   ✓ Vista lista creada")
    except Exception as e:
        print(f"   ⚠ Vista lista: {e}")
    
    # Vista formulario
    vista_form = """<?xml version="1.0"?>
<form string="Trasferencia Dashboard">
    <sheet>
        <group>
            <group>
                <field name="x_name"/>
                <field name="x_fecha_hora"/>
                <field name="x_paquete_id"/>
                <field name="x_ubicacion_origen_id"/>
                <field name="x_ubicacion_destino_id"/>
            </group>
            <group>
                <field name="x_usuario_id"/>
                <field name="x_total_kg"/>
                <field name="x_cantidad_quants"/>
                <field name="x_estado"/>
                <field name="x_origen_sistema"/>
            </group>
        </group>
        <group>
            <field name="x_detalles" nolabel="1"/>
        </group>
    </sheet>
</form>"""
    
    try:
        odoo.execute("ir.ui.view", "create", {
            "name": "x_trasferencias_dashboard.form",
            "model": "x_trasferencias_dashboard",
            "type": "form",
            "arch": vista_form
        })
        print("   ✓ Vista formulario creada")
    except Exception as e:
        print(f"   ⚠ Vista formulario: {e}")
    
    print("\n" + "=" * 80)
    print("CONFIGURACIÓN COMPLETADA")
    print("=" * 80)
    print(f"\n✅ Modelo limpio y configurado correctamente")
    print(f"\nNOTA: Refresca el navegador (F5 o Ctrl+F5) para ver los cambios")


if __name__ == "__main__":
    main()
