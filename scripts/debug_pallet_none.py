"""Debug: Verificar pallets que causan producto_id=None."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

odoo = OdooClient(
    url="https://riofuturo.server98c6e.oerpondemand.net",
    db="riofuturo-master",
    username=USERNAME,
    password=PASSWORD
)

pallets = ['PACK0021869']  # El pallet problemático

print("=" * 80)
print("INVESTIGACIÓN PROFUNDA DE PACK0021869")
print("=" * 80)

# 1. Buscar el package
packages = odoo.search_read('stock.quant.package', [('name', '=', 'PACK0021869')], ['id', 'name'])
if not packages:
    print("❌ Package NO ENCONTRADO")
    exit(1)

pkg = packages[0]
print(f"\n✅ Package encontrado: ID={pkg['id']}, Name={pkg['name']}")

# 2. Buscar TODOS los quants (incluso con qty=0)
all_quants = odoo.search_read('stock.quant', [('package_id', '=', pkg['id'])], 
                              ['package_id', 'product_id', 'quantity', 'lot_id', 'location_id'])

print(f"\n📦 Total de quants encontrados (incluyendo qty=0): {len(all_quants)}")
for q in all_quants:
    prod_id = q['product_id'][0] if q['product_id'] else None
    prod_name = q['product_id'][1] if q['product_id'] else 'SIN PRODUCTO'
    qty = q['quantity']
    location = q['location_id'][1] if q.get('location_id') else 'Sin ubicación'
    lote = q['lot_id'][1] if q.get('lot_id') else 'Sin lote'
    
    status = "✅" if prod_id else "❌"
    print(f"  {status} Qty: {qty} kg - producto_id: {prod_id} - {prod_name}")
    print(f"      Ubicación: {location}")
    print(f"      Lote: {lote}")
    print()

# 3. Simular lo que hace el validador
print("=" * 80)
print("SIMULANDO VALIDACIÓN")
print("=" * 80)

from backend.services.tuneles.pallet_validator import validar_pallets_batch

result = validar_pallets_batch(odoo, ['PACK0021869'], buscar_ubicacion=False)
print(f"\nResultado de validación:")
import json
print(json.dumps(result, indent=2, default=str))
