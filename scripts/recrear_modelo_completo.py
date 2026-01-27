"""
Script para forzar recreación del modelo

Uso:
    python scripts/recrear_modelo_completo.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

def main():
    """Recrear el modelo completamente."""
    
    print("=" * 80)
    print("RECREANDO MODELO COMPLETO")
    print("=" * 80)
    
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("\n✓ Conectado a Odoo")
    
    # 1. Buscar y eliminar el modelo viejo
    print("\n1. Eliminando modelo viejo...")
    models = odoo.search("ir.model", [("model", "=", "x_trasferencias_dashboard")])
    if models:
        # Primero eliminar todos los registros
        try:
            records = odoo.search("x_trasferencias_dashboard", [])
            if records:
                odoo.execute("x_trasferencias_dashboard", "unlink", records)
                print(f"   ✓ Eliminados {len(records)} registros")
        except:
            pass
        
        # Eliminar el modelo (los campos quedarán huérfanos pero no importa)
        odoo.execute("ir.model", "unlink", models)
        print(f"   ✓ Modelo eliminado (ID: {models[0]})")
    
    # 2. Crear modelo nuevo
    print("\n2. Creando modelo nuevo...")
    model_id = odoo.execute("ir.model", "create", {
        "name": "Trasferencias Dashboard",
        "model": "x_trasferencias_dashboard_v2",
        "state": "manual"
    })
    print(f"   ✓ Modelo creado (ID: {model_id})")
    
    # 3. Crear campos
    print("\n3. Creando campos...")
    
    campos = [
        {
            "name": "x_name",
            "field_description": "Nombre/Referencia",
            "ttype": "char",
            "state": "manual"
        },
        {
            "name": "x_fecha_hora",
            "field_description": "Fecha y Hora",
            "ttype": "datetime",
            "state": "manual"
        },
        {
            "name": "x_paquete_id",
            "field_description": "Paquete",
            "ttype": "many2one",
            "relation": "stock.quant.package",
            "state": "manual"
        },
        {
            "name": "x_ubicacion_origen_id",
            "field_description": "Ubicación Origen",
            "ttype": "many2one",
            "relation": "stock.location",
            "state": "manual"
        },
        {
            "name": "x_ubicacion_destino_id",
            "field_description": "Ubicación Destino",
            "ttype": "many2one",
            "relation": "stock.location",
            "state": "manual"
        },
        {
            "name": "x_usuario_id",
            "field_description": "Usuario",
            "ttype": "many2one",
            "relation": "res.users",
            "state": "manual"
        },
        {
            "name": "x_total_kg",
            "field_description": "Total KG",
            "ttype": "float",
            "state": "manual"
        },
        {
            "name": "x_cantidad_quants",
            "field_description": "Cantidad Quants Movidos",
            "ttype": "integer",
            "state": "manual"
        },
        {
            "name": "x_detalles",
            "field_description": "Detalles Productos/Lotes",
            "ttype": "text",
            "state": "manual"
        },
        {
            "name": "x_estado",
            "field_description": "Estado",
            "ttype": "selection",
            "selection": "[('completado', 'Completado'), ('error', 'Error'), ('pendiente', 'Pendiente')]",
            "state": "manual"
        },
        {
            "name": "x_origen_sistema",
            "field_description": "Origen Sistema",
            "ttype": "selection",
            "selection": "[('dashboard', 'Dashboard Web'), ('api', 'API'), ('manual', 'Manual')]",
            "state": "manual"
        }
    ]
    
    for campo in campos:
        campo["model_id"] = model_id
        try:
            field_id = odoo.execute("ir.model.fields", "create", campo)
            print(f"   ✓ {campo['field_description']}")
        except Exception as e:
            if "Field names must be unique" in str(e):
                print(f"   - {campo['field_description']} (ya existe)")
            else:
                print(f"   ⚠ {campo['field_description']}: {e}")
    
    # 4. Crear action
    print("\n4. Creando action...")
    action_id = odoo.execute("ir.actions.act_window", "create", {
        "name": "Logs",
        "res_model": "x_trasferencias_dashboard_v2",
        "view_mode": "tree,form"
    })
    print(f"   ✓ Action creado (ID: {action_id})")
    
    # 5. Crear menú
    print("\n5. Creando menú...")
    
    # Menú padre
    parent_menu_id = odoo.execute("ir.ui.menu", "create", {
        "name": "Trasferencias Dashboard",
        "action": f"ir.actions.act_window,{action_id}"
    })
    print(f"   ✓ Menú padre creado (ID: {parent_menu_id})")
    
    # Submenú
    submenu_id = odoo.execute("ir.ui.menu", "create", {
        "name": "Logs",
        "parent_id": parent_menu_id,
        "action": f"ir.actions.act_window,{action_id}"
    })
    print(f"   ✓ Submenú creado (ID: {submenu_id})")
    
    # 6. Crear vistas
    print("\n6. Creando vistas...")
    
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
    
    odoo.execute("ir.ui.view", "create", {
        "name": "x_trasferencias_dashboard_v2.tree",
        "model": "x_trasferencias_dashboard_v2",
        "type": "tree",
        "arch": vista_tree
    })
    print("   ✓ Vista lista creada")
    
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
    
    odoo.execute("ir.ui.view", "create", {
        "name": "x_trasferencias_dashboard_v2.form",
        "model": "x_trasferencias_dashboard_v2",
        "type": "form",
        "arch": vista_form
    })
    print("   ✓ Vista formulario creada")
    
    print("\n" + "=" * 80)
    print("✅ MODELO RECREADO EXITOSAMENTE")
    print("=" * 80)
    print(f"\nModelo ID: {model_id}")
    print(f"Menú ID: {parent_menu_id}")
    print(f"\n⚠️  IMPORTANTE: Refresca el navegador (Ctrl+F5)")


if __name__ == "__main__":
    main()
