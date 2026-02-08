"""
Script para eliminar A8 y B8 de Cámara 2 VLK
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

client = OdooClient(
    username=ODOO_USER,
    password=ODOO_PASSWORD,
    url=ODOO_URL,
    db=ODOO_DB
)

print("=" * 80)
print("Eliminando A8 y B8 de Cámara 2 VLK")
print("=" * 80)

# Buscar las ubicaciones A8 y B8 de Cámara 2
locations_to_delete = client.search_read(
    'stock.location',
    [['barcode', 'in', ['CAM2VLKA8', 'CAM2VLKB8']]],
    ['id', 'name', 'barcode', 'complete_name']
)

if not locations_to_delete:
    print("\n✅ No se encontraron CAM2VLKA8 o CAM2VLKB8 - ya están eliminadas")
else:
    print(f"\n🔍 Encontradas {len(locations_to_delete)} ubicaciones para eliminar:")
    
    for loc in locations_to_delete:
        print(f"\n   ID: {loc['id']} - {loc['barcode']} ({loc['complete_name']})")
        
        # Verificar que no tenga stock
        quants = client.search_read(
            'stock.quant',
            [['location_id', '=', loc['id']], ['quantity', '>', 0]],
            ['id']
        )
        
        if quants:
            print(f"   ❌ ERROR: Tiene {len(quants)} quants con stock - no se puede eliminar")
            continue
        
        # Eliminar
        try:
            client.models.execute_kw(
                client.db, client.uid, client.password,
                'stock.location', 'unlink',
                [[loc['id']]]
            )
            print(f"   ✅ Eliminada correctamente")
        except Exception as e:
            print(f"   ❌ Error: {e}")

print("\n" + "=" * 80)
print("✅ Proceso completado")
print("=" * 80)
print("\nCámara 2 ahora tiene:")
print("  - A1, A2, A3, A4, A5, A6, A7 (7 posiciones)")
print("  - B1, B2, B3, B4, B5, B6, B7 (7 posiciones)")
print("  Total: 14 posiciones")
