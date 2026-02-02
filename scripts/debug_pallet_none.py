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

pallets = [
    'PACK0021850', 'PACK0021851', 'PACK0021856', 'PACK0021859', 'PACK0021869',
    'PACK0021197', 'PACK0021198', 'PACK0021916', 'PACK0021814', 'PACK0021802',
    'PACK0022359', 'PACK0022278', 'PACK0022319', 'PACK0023486', 'PACK0022635'
]

print("=" * 80)
print("VERIFICANDO PALLETS - BÚSQUEDA DE producto_id=None")
print("=" * 80)

packages = odoo.search_read('stock.quant.package', [('name', 'in', pallets)], ['id', 'name'])
pkg_map = {p['name']: p['id'] for p in packages}
pkg_ids = [p['id'] for p in packages]

print(f"\nPackages encontrados: {len(packages)}/{len(pallets)}")

quants = odoo.search_read('stock.quant', [('package_id', 'in', pkg_ids), ('quantity', '>', 0)], 
                          ['package_id', 'product_id', 'quantity', 'lot_id', 'location_id'])

print(f"Quants con stock: {len(quants)}\n")

# Agrupar por producto para ver totales
productos_totales = {}

for pallet in pallets:
    pkg_id = pkg_map.get(pallet)
    if not pkg_id:
        print(f"❌ {pallet}: NO ENCONTRADO EN ODOO")
        continue
    
    pallet_quants = [q for q in quants if q['package_id'][0] == pkg_id]
    if pallet_quants:
        for q in pallet_quants:
            prod_id = q['product_id'][0] if q['product_id'] else None
            prod_name = q['product_id'][1] if q['product_id'] else 'SIN PRODUCTO'
            qty = q['quantity']
            lote = q['lot_id'][1] if q.get('lot_id') else 'Sin lote'
            
            if prod_id is None:
                print(f"⚠️  {pallet}: {qty} kg - producto_id=None - lote={lote} ❌ PROBLEMA!")
            else:
                print(f"✅ {pallet}: {qty} kg - producto_id={prod_id} - {prod_name}")
                
                # Agregar a totales
                if prod_id not in productos_totales:
                    productos_totales[prod_id] = {'kg': 0, 'pallets': []}
                productos_totales[prod_id]['kg'] += qty
                productos_totales[prod_id]['pallets'].append({
                    'codigo': pallet,
                    'kg': qty,
                    'producto_id': prod_id
                })
    else:
        print(f"⚠️  {pallet}: SIN STOCK (package existe pero 0 quants)")

print("\n" + "=" * 80)
print("TOTALES POR PRODUCTO")
print("=" * 80)
for prod_id, data in productos_totales.items():
    if prod_id is None:
        print(f"producto_id=None: {data['kg']} kg - {len(data['pallets'])} pallets ❌")
    else:
        print(f"producto_id={prod_id}: {data['kg']} kg - {len(data['pallets'])} pallets")
