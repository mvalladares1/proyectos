"""
Debug: Ver qué tipo_fruta tienen los productos realmente producidos
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*140)
print("DEBUG: TIPO_FRUTA DE PRODUCTOS PRODUCIDOS")
print("="*140)

# Orden 00762
orden_id = 4980

# Producciones
producciones = odoo.search_read(
    'stock.move',
    [
        ['production_id', '=', orden_id],
        ['state', '=', 'done']
    ],
    ['product_id', 'quantity_done'],
    limit=20
)

print(f"\nProductos producidos en orden {orden_id}:")

prod_ids = [p.get('product_id', [None])[0] for p in producciones if p.get('product_id')]
productos = odoo.search_read(
    'product.product',
    [['id', 'in', prod_ids]],
    ['id', 'name', 'x_studio_sub_categora'],
    limit=20
)

productos_map = {}
for p in productos:
    sub_cat = p.get('x_studio_sub_categora')
    if isinstance(sub_cat, (list, tuple)) and len(sub_cat) > 1:
        tipo_str = sub_cat[1]
    else:
        tipo_str = 'Sin clasificar'
    
    productos_map[p['id']] = {
        'nombre': p['name'],
        'tipo_fruta': tipo_str
    }

print(f"\n{'='*140}")
print(f"{'PRODUCTO':<60} {'KG':>12} {'TIPO_FRUTA':<30} {'FILTRADO':>15}")
print(f"{'='*140}")

for prod in producciones:
    prod_id = prod.get('product_id', [None])[0]
    if not prod_id or prod_id not in productos_map:
        continue
    
    kg = prod.get('quantity_done', 0)
    nombre = productos_map[prod_id]['nombre'][:60]
    tipo_fruta = productos_map[prod_id]['tipo_fruta'][:30]
    
    # Aplicar filtro
    filtrado = "SÍ INCLUYE"
    if nombre.upper().startswith('PROCESO ') or 'MERMA' in nombre.upper():
        filtrado = "EXCLUÍDO"
    
    print(f"{nombre:<60} {kg:>12.2f} {tipo_fruta:<30} {filtrado:>15}")

print(f"\n{'='*140}")
