"""
Script para actualizar y crear ubicaciones VLK organizadas por cámara
1. Actualiza barcodes de Cámara 1: CAMVLK* → CAM1VLK*
2. Crea ubicaciones de Cámara 2 con barcodes CAM2VLK*
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
print("PASO 1: Actualizar barcodes de Cámara 1 (CAMVLK → CAM1VLK)")
print("=" * 80)

# Buscar ubicaciones de Cámara 1 -25°C
camara1_locations = client.search_read(
    'stock.location',
    [['complete_name', 'ilike', 'VLK/Camara 1 -25°C'], ['barcode', '!=', False]],
    ['id', 'name', 'barcode', 'complete_name']
)

print(f"\n✅ Encontradas {len(camara1_locations)} ubicaciones en Cámara 1")

for loc in camara1_locations:
    old_barcode = loc['barcode']
    if old_barcode and old_barcode.startswith('CAMVLK'):
        # Extraer el código de posición (A1, B1, etc)
        position_code = old_barcode.replace('CAMVLK', '')
        new_barcode = f'CAM1VLK{position_code}'
        
        # Actualizar en Odoo
        client.models.execute_kw(
            client.db, client.uid, client.password,
            'stock.location', 'write',
            [[loc['id']], {'barcode': new_barcode}]
        )
        
        print(f"   {loc['name']}: {old_barcode} → {new_barcode}")

print("\n" + "=" * 80)
print("PASO 2: Crear ubicaciones para Cámara 2 -25°C")
print("=" * 80)

# Buscar ID de Cámara 2
camara2_parent = client.search_read(
    'stock.location',
    [['complete_name', '=', 'VLK/Camara 2 -25°C']],
    ['id', 'name']
)

if not camara2_parent:
    print("\n❌ ERROR: No se encontró 'VLK/Camara 2 -25°C'")
    print("   Verifica que exista en Odoo")
    sys.exit(1)

parent_id = camara2_parent[0]['id']
print(f"\n✅ Cámara 2 encontrada (ID: {parent_id})")

# Definir posiciones para Cámara 2
positions = []

# Fila A: A1-A8
for i in range(1, 9):
    positions.append({
        'name': f'A{i}',
        'barcode': f'CAM2VLKA{i}',
        'location_id': parent_id,
        'usage': 'internal',
        'active': True
    })

# Fila B: B1-B8
for i in range(1, 9):
    positions.append({
        'name': f'B{i}',
        'barcode': f'CAM2VLKB{i}',
        'location_id': parent_id,
        'usage': 'internal',
        'active': True
    })

print(f"\n🔨 Creando {len(positions)} ubicaciones en Cámara 2...")

created_count = 0
for pos in positions:
    # Verificar si ya existe
    existing = client.search_read(
        'stock.location',
        [['barcode', '=', pos['barcode']]],
        ['id']
    )
    
    if existing:
        print(f"   ⚠️  {pos['name']} ({pos['barcode']}) ya existe - omitiendo")
        continue
    
    # Crear ubicación
    new_id = client.models.execute_kw(
        client.db, client.uid, client.password,
        'stock.location', 'create',
        [pos]
    )
    
    print(f"   ✅ {pos['name']} ({pos['barcode']}) creada - ID: {new_id}")
    created_count += 1

print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)
print(f"✅ Barcodes de Cámara 1 actualizados: {len(camara1_locations)}")
print(f"✅ Ubicaciones nuevas en Cámara 2: {created_count}")
print(f"\n📋 Total de ubicaciones VLK: {len(camara1_locations) + created_count}")
print("\nCámara 1: CAM1VLKA1-A8, CAM1VLKB1-B8 (16 posiciones)")
print("Cámara 2: CAM2VLKA1-A8, CAM2VLKB1-B8 (16 posiciones)")
print("Total: 32 posiciones")
