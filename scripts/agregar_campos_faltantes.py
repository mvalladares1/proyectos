"""
Script para agregar los campos many2one faltantes

Uso:
    python scripts/agregar_campos_faltantes.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

def main():
    """Agrega los campos many2one faltantes."""
    
    print("=" * 80)
    print("AGREGANDO CAMPOS MANY2ONE FALTANTES")
    print("=" * 80)
    
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("\n✓ Conectado a Odoo")
    
    # Buscar el modelo
    models = odoo.search_read(
        "ir.model",
        [("model", "=", "x_trasferencias_dashboard")],
        ["id"]
    )
    model_id = models[0]["id"]
    print(f"✓ Modelo ID: {model_id}")
    
    # Campos many2one a crear
    campos = [
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
        }
    ]
    
    print("\n📝 Creando campos...")
    for campo in campos:
        campo["model_id"] = model_id
        try:
            field_id = odoo.execute("ir.model.fields", "create", campo)
            print(f"   ✓ {campo['field_description']}: {campo['name']}")
        except Exception as e:
            print(f"   ⚠ {campo['name']}: {e}")
    
    print("\n" + "=" * 80)
    print("✅ CAMPOS AGREGADOS CORRECTAMENTE")
    print("=" * 80)


if __name__ == "__main__":
    main()
