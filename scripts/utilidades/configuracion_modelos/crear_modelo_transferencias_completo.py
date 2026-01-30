"""
Script para crear el modelo completo "Trasferencias Dashboard" desde cero

Uso:
    python scripts/crear_modelo_transferencias_completo.py
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
    """Crea el modelo completo de Trasferencias Dashboard."""
    
    print("=" * 80)
    print("CREACIÓN COMPLETA DEL MODELO TRASFERENCIAS DASHBOARD")
    print("=" * 80)
    
    # Conectar a Odoo
    print("\n1. Conectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("   ✓ Conectado exitosamente")
    
    # Crear el modelo
    print("\n2. Creando modelo 'Trasferencias Dashboard'...")
    
    model_vals = {
        "name": "Trasferencias Dashboard",
        "model": "x_trasferencias_dashboard",
        "state": "manual",
        "field_id": []
    }
    
    try:
        model_id = odoo.execute("ir.model", "create", model_vals)
        print(f"   ✓ Modelo creado (ID: {model_id})")
    except Exception as e:
        print(f"   ✗ Error creando modelo: {e}")
        # Si ya existe, buscarlo
        models = odoo.search_read(
            "ir.model",
            [("model", "=", "x_trasferencias_dashboard")],
            ["id", "name"]
        )
        if models:
            model_id = models[0]["id"]
            print(f"   ⚠ Modelo ya existe, usando existente (ID: {model_id})")
        else:
            print("   ✗ No se pudo crear ni encontrar el modelo")
            return
    
    # Campos a crear
    print("\n3. Creando campos...")
    
    campos = [
        {
            "name": "x_name",
            "field_description": "Nombre/Referencia",
            "ttype": "char",
            "required": True,
            "model_id": model_id,
            "state": "manual"
        },
        {
            "name": "x_fecha_hora",
            "field_description": "Fecha y Hora",
            "ttype": "datetime",
            "required": True,
            "model_id": model_id,
            "state": "manual"
        },
        {
            "name": "x_paquete_id",
            "field_description": "Paquete",
            "ttype": "many2one",
            "relation": "stock.quant.package",
            "required": True,
            "model_id": model_id,
            "state": "manual"
        },
        {
            "name": "x_ubicacion_origen_id",
            "field_description": "Ubicación Origen",
            "ttype": "many2one",
            "relation": "stock.location",
            "required": True,
            "model_id": model_id,
            "state": "manual"
        },
        {
            "name": "x_ubicacion_destino_id",
            "field_description": "Ubicación Destino",
            "ttype": "many2one",
            "relation": "stock.location",
            "required": True,
            "model_id": model_id,
            "state": "manual"
        },
        {
            "name": "x_usuario_id",
            "field_description": "Usuario",
            "ttype": "many2one",
            "relation": "res.users",
            "model_id": model_id,
            "state": "manual"
        },
        {
            "name": "x_total_kg",
            "field_description": "Total KG",
            "ttype": "float",
            "model_id": model_id,
            "state": "manual"
        },
        {
            "name": "x_cantidad_quants",
            "field_description": "Cantidad Quants Movidos",
            "ttype": "integer",
            "model_id": model_id,
            "state": "manual"
        },
        {
            "name": "x_detalles",
            "field_description": "Detalles Productos/Lotes",
            "ttype": "text",
            "model_id": model_id,
            "state": "manual"
        },
        {
            "name": "x_estado",
            "field_description": "Estado",
            "ttype": "selection",
            "selection": "[('success','Exitoso'),('error','Con Errores'),('partial','Parcial')]",
            "model_id": model_id,
            "state": "manual"
        },
        {
            "name": "x_origen_sistema",
            "field_description": "Origen Sistema",
            "ttype": "selection",
            "selection": "[('dashboard_web','Dashboard Web'),('dashboard_mobile','Dashboard Móvil'),('script','Script Manual')]",
            "model_id": model_id,
            "state": "manual"
        }
    ]
    
    campos_creados = 0
    for campo in campos:
        try:
            field_id = odoo.execute("ir.model.fields", "create", campo)
            campos_creados += 1
            print(f"   ✓ {campo['field_description']} ({campo['ttype']})")
        except Exception as e:
            print(f"   ✗ Error en {campo['field_description']}: {e}")
    
    # Crear vistas básicas
    print("\n4. Creando vistas...")
    
    # Vista lista
    vista_tree = f"""<?xml version="1.0"?>
<tree string="Trasferencias Dashboard">
    <field name="x_name"/>
    <field name="x_fecha_hora"/>
    <field name="x_paquete_id"/>
    <field name="x_ubicacion_origen_id"/>
    <field name="x_ubicacion_destino_id"/>
    <field name="x_total_kg"/>
    <field name="x_estado"/>
</tree>"""
    
    try:
        tree_id = odoo.execute("ir.ui.view", "create", {
            "name": "Trasferencias Dashboard Tree",
            "model": "x_trasferencias_dashboard",
            "type": "tree",
            "arch": vista_tree
        })
        print(f"   ✓ Vista lista creada")
    except Exception as e:
        print(f"   ⚠ Vista lista: {e}")
    
    # Vista formulario
    vista_form = f"""<?xml version="1.0"?>
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
        form_id = odoo.execute("ir.ui.view", "create", {
            "name": "Trasferencias Dashboard Form",
            "model": "x_trasferencias_dashboard",
            "type": "form",
            "arch": vista_form
        })
        print(f"   ✓ Vista formulario creada")
    except Exception as e:
        print(f"   ⚠ Vista formulario: {e}")
    
    # Crear acción de menú
    print("\n5. Creando acción de menú...")
    
    try:
        action_id = odoo.execute("ir.actions.act_window", "create", {
            "name": "Trasferencias Dashboard",
            "res_model": "x_trasferencias_dashboard",
            "view_mode": "tree,form",
            "domain": "[]",
            "context": "{}",
            "help": "Registro de transferencias realizadas desde el Dashboard"
        })
        print(f"   ✓ Acción creada (ID: {action_id})")
        
        # Crear menú
        menu_id = odoo.execute("ir.ui.menu", "create", {
            "name": "Trasferencias Dashboard",
            "action": f"ir.actions.act_window,{action_id}",
            "parent_id": False  # Menú raíz
        })
        print(f"   ✓ Menú creado (ID: {menu_id})")
    except Exception as e:
        print(f"   ⚠ Menú: {e}")
    
    print("\n" + "=" * 80)
    print("CREACIÓN COMPLETADA")
    print("=" * 80)
    print(f"\nRESUMEN:")
    print(f"  - Modelo: x_trasferencias_dashboard")
    print(f"  - Campos creados: {campos_creados}/{len(campos)}")
    print(f"\n✅ El modelo está listo para registrar transferencias")
    print(f"\nPuedes acceder desde: Aplicaciones > Trasferencias Dashboard")


if __name__ == "__main__":
    main()
