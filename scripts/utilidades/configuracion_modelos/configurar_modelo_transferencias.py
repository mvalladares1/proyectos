"""
Script para configurar el modelo "Trasferencias Dashboard" vía API
Agrega campos necesarios y limpia los que no sirven

Uso:
    python scripts/configurar_modelo_transferencias.py
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
    """Configura el modelo de Trasferencias Dashboard."""
    
    print("=" * 80)
    print("CONFIGURACIÓN DEL MODELO TRASFERENCIAS DASHBOARD")
    print("=" * 80)
    
    # Conectar a Odoo
    print("\n1. Conectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("   ✓ Conectado exitosamente")
    
    # Buscar el modelo
    print("\n2. Buscando modelos personalizados recientes...")
    models = odoo.search_read(
        "ir.model",
        [("model", "like", "x_")],
        ["id", "name", "model"],
        order="create_date desc",
        limit=10
    )
    
    print(f"   Modelos encontrados: {len(models)}")
    for m in models:
        print(f"     - {m['name']} ({m['model']})")
    
    # Buscar el que contiene "trasferencia" o "log"
    model = None
    for m in models:
        if "trasferencia" in m['name'].lower() or "log" in m['name'].lower():
            model = m
            break
    
    if not model:
        print("\n   ✗ ERROR: No se encontró el modelo de Trasferencias Dashboard")
        print("   Por favor verifica el nombre exacto en Odoo Studio")
        return
    model_id = model["id"]
    model_name = model["model"]
    print(f"   ✓ Modelo encontrado: {model['name']}")
    print(f"     - ID: {model_id}")
    print(f"     - Nombre técnico: {model_name}")
    
    # Obtener campos actuales
    print("\n3. Obteniendo campos actuales...")
    current_fields = odoo.search_read(
        "ir.model.fields",
        [("model_id", "=", model_id), ("state", "=", "manual")],
        ["id", "name", "field_description", "ttype"]
    )
    
    print(f"   ✓ Campos actuales: {len(current_fields)}")
    for field in current_fields:
        print(f"     - {field['name']}: {field['field_description']} ({field['ttype']})")
    
    # Campos a eliminar (los que no sirven)
    campos_a_eliminar = []
    for field in current_fields:
        if field['name'] in ['x_studio_responsable', 'x_studio_new_html', 'x_studio_pedido_de_compra', 
                             'x_studio_contacto', 'x_studio_telfono', 'x_studio_correo_electrnico']:
            campos_a_eliminar.append(field)
    
    if campos_a_eliminar:
        print(f"\n4. Eliminando {len(campos_a_eliminar)} campos innecesarios...")
        for field in campos_a_eliminar:
            try:
                odoo.execute("ir.model.fields", "unlink", [field['id']])
                print(f"   ✓ Eliminado: {field['field_description']}")
            except Exception as e:
                print(f"   ✗ Error eliminando {field['field_description']}: {e}")
    
    # Campos a crear
    print("\n5. Creando campos necesarios...")
    
    campos_nuevos = [
        {
            "name": "x_studio_paquete",
            "field_description": "Paquete",
            "ttype": "many2one",
            "relation": "stock.quant.package",
            "required": True,
            "model_id": model_id
        },
        {
            "name": "x_studio_ubicacion_origen",
            "field_description": "Ubicación Origen",
            "ttype": "many2one",
            "relation": "stock.location",
            "required": True,
            "model_id": model_id
        },
        {
            "name": "x_studio_ubicacion_destino",
            "field_description": "Ubicación Destino",
            "ttype": "many2one",
            "relation": "stock.location",
            "required": True,
            "model_id": model_id
        },
        {
            "name": "x_studio_usuario",
            "field_description": "Usuario",
            "ttype": "many2one",
            "relation": "res.users",
            "model_id": model_id
        },
        {
            "name": "x_studio_total_kg",
            "field_description": "Total KG",
            "ttype": "float",
            "model_id": model_id
        },
        {
            "name": "x_studio_cantidad_quants",
            "field_description": "Cantidad Quants Movidos",
            "ttype": "integer",
            "model_id": model_id
        },
        {
            "name": "x_studio_detalles",
            "field_description": "Detalles Productos/Lotes",
            "ttype": "text",
            "model_id": model_id
        },
        {
            "name": "x_studio_estado",
            "field_description": "Estado",
            "ttype": "selection",
            "selection": "[('success','Exitoso'),('error','Con Errores'),('partial','Parcial')]",
            "model_id": model_id
        },
        {
            "name": "x_studio_origen_sistema",
            "field_description": "Origen Sistema",
            "ttype": "selection",
            "selection": "[('dashboard_web','Dashboard Web'),('dashboard_mobile','Dashboard Móvil'),('script','Script Manual')]",
            "model_id": model_id
        },
        {
            "name": "x_studio_fecha_hora",
            "field_description": "Fecha y Hora",
            "ttype": "datetime",
            "required": True,
            "model_id": model_id
        }
    ]
    
    campos_creados = 0
    for campo in campos_nuevos:
        try:
            # Verificar si ya existe
            existing = odoo.search_read(
                "ir.model.fields",
                [("model_id", "=", model_id), ("name", "=", campo["name"])],
                ["id"]
            )
            
            if existing:
                print(f"   ⚠ Ya existe: {campo['field_description']}")
                continue
            
            # Crear el campo
            odoo.execute("ir.model.fields", "create", campo)
            campos_creados += 1
            print(f"   ✓ Creado: {campo['field_description']} ({campo['ttype']})")
        except Exception as e:
            print(f"   ✗ Error creando {campo['field_description']}: {e}")
    
    # Verificar campos finales
    print("\n6. Verificando configuración final...")
    final_fields = odoo.search_read(
        "ir.model.fields",
        [("model_id", "=", model_id), ("state", "=", "manual")],
        ["name", "field_description", "ttype", "required"]
    )
    
    print(f"\n   ✓ Campos finales: {len(final_fields)}")
    for field in final_fields:
        req = " [REQUERIDO]" if field.get('required') else ""
        print(f"     - {field['field_description']}: {field['ttype']}{req}")
    
    print("\n" + "=" * 80)
    print("CONFIGURACIÓN COMPLETADA")
    print("=" * 80)
    print(f"\nRESUMEN:")
    print(f"  - Modelo: {model['name']}")
    print(f"  - Campos eliminados: {len(campos_a_eliminar)}")
    print(f"  - Campos creados: {campos_creados}")
    print(f"  - Total campos: {len(final_fields)}")
    print(f"\n✅ El modelo está listo para registrar transferencias del dashboard")


if __name__ == "__main__":
    main()
