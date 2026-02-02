"""Script para verificar pallets en Odoo."""
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
from shared.odoo_client import OdooClient

odoo = OdooClient()

pallets = [
    'PACK0021850', 'PACK0021851', 'PACK0021856', 'PACK0021859', 'PACK0021869',
    'PACK0021197', 'PACK0021198', 'PACK0021916', 'PACK0021814', 'PACK0021802',
    'PACK0022359', 'PACK0022278', 'PACK0022319', 'PACK0023486', 'PACK0022635'
]

packages = odoo.search_read('stock.quant.package', [('name', 'in', pallets)], ['id', 'name'])
pkg_map = {p['name']: p['id'] for p in packages}
pkg_ids = [p['id'] for p in packages]

quants = odoo.search_read('stock.quant', [('package_id', 'in', pkg_ids), ('quantity', '>', 0)], ['package_id', 'product_id', 'quantity', 'lot_id'])

print("=== ESTADO DE PALLETS ===\n")
for pallet in pallets:
    pkg_id = pkg_map.get(pallet)
    if not pkg_id:
        print(f"{pallet}: NO ENCONTRADO EN ODOO")
        continue
    
    pallet_quants = [q for q in quants if q['package_id'][0] == pkg_id]
    if pallet_quants:
        for q in pallet_quants:
            prod_name = q['product_id'][1] if q['product_id'] else 'SIN PRODUCTO'
            prod_id = q['product_id'][0] if q['product_id'] else None
            print(f"{pallet}: {q['quantity']} kg - producto_id={prod_id} - {prod_name}")
    else:
        print(f"{pallet}: SIN STOCK (package existe pero 0 quants)")
