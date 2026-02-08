"""
Agregar campo x_bodega (selection) al modelo x_trasferencias_dashboard_v2
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.odoo_client import OdooClient

client = OdooClient(
    username='mvalladares@riofuturo.cl',
    password='c0766224bec30cac071ffe43a858c9ccbd521ddd',
    url='https://riofuturo.server98c6e.oerpondemand.net',
    db='riofuturo-master'
)

# Primero buscar el ID del modelo
model_info = client.search_read(
    'ir.model',
    [['model', '=', 'x_trasferencias_dashboard_v2']],
    ['id', 'name']
)

if not model_info:
    print("❌ Modelo no encontrado")
    exit(1)

model_id = model_info[0]['id']
print(f"✅ Modelo encontrado: ID={model_id}")

# Verificar si el campo ya existe
existing = client.search_read(
    'ir.model.fields',
    [['model', '=', 'x_trasferencias_dashboard_v2'], ['name', '=', 'x_bodega']],
    ['id']
)

if existing:
    print(f"⚠️ El campo x_bodega ya existe (ID={existing[0]['id']})")
else:
    # Crear el campo selection para bodega
    field_vals = {
        'name': 'x_bodega',
        'field_description': 'Bodega',
        'model_id': model_id,
        'ttype': 'selection',
        'selection_ids': [
            (0, 0, {'value': 'VLK', 'name': 'Vilkun', 'sequence': 1}),
            (0, 0, {'value': 'RF', 'name': 'Río Futuro', 'sequence': 2}),
        ],
        'store': True,
        'copied': True,
    }
    
    try:
        field_id = client.models.execute_kw(
            client.db, client.uid, client.password,
            'ir.model.fields', 'create', [field_vals]
        )
        print(f"✅ Campo x_bodega creado correctamente (ID={field_id})")
    except Exception as e:
        print(f"❌ Error creando campo: {e}")

# Verificar que se creó
print("\n📋 Campos actuales:")
fields = client.search_read(
    'ir.model.fields',
    [['model', '=', 'x_trasferencias_dashboard_v2'], ['name', 'like', 'x_']],
    ['name', 'field_description', 'ttype']
)
for f in fields:
    print(f"  {f['name']:<30} | {f['ttype']:<15} | {f['field_description']}")
