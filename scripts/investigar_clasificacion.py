"""
Investigar por qué todos los productos aparecen como "Sin clasificar"
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*140)
print("INVESTIGACIÓN: PRODUCTOS SIN CLASIFICAR")
print("="*140)

# Obtener una orden de ejemplo
orden = odoo.search_read(
    'mrp.production',
    [['name', '=', 'WH/RF/MOV/RETAIL/00762']],
    ['id', 'product_id'],
    limit=1
)[0]

prod_id = orden['product_id'][0]
prod_name = orden['product_id'][1]

print(f"\nProducto final de orden 00762: {prod_name}")
print(f"ID: {prod_id}")

# Obtener todos los campos del producto
producto = odoo.search_read(
    'product.product',
    [['id', '=', prod_id]],
    ['name', 'default_code', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo', 
     'categ_id'],
    limit=1
)[0]

print(f"\nCampos del producto:")
for campo, valor in producto.items():
    print(f"   {campo}: {valor}")

# Buscar campo correcto para tipo de fruta
print(f"\n{'='*140}")
print(f"BUSCANDO CAMPO CORRECTO PARA TIPO DE FRUTA")
print(f"{'='*140}")

# Obtener model metadata
print(f"\nInspeccionando modelo product.product...")

# Probar diferentes productos
ordenes = odoo.search_read(
    'mrp.production',
    [['state', '=', 'done']],
    ['id', 'product_id'],
    limit=20
)

print(f"\nAnalizando {len(ordenes)} productos finales de órdenes...")

prod_ids = [o['product_id'][0] for o in ordenes if o.get('product_id')]
productos = odoo.search_read(
    'product.product',
    [['id', 'in', prod_ids]],
    ['id', 'name', 'default_code', 'x_studio_sub_categora', 'categ_id'],
    limit=20
)

print(f"\n{'='*140}")
print(f"{'PRODUCTO':<60} {'CATEG_ID':<30} {'X_STUDIO_SUB':<20}")
print(f"{'='*140}")

for p in productos[:10]:
    nombre = p['name'][:60]
    categ = p.get('categ_id', [None, 'N/A'])[1] if p.get('categ_id') else 'N/A'
    categ = categ[:30]
    
    sub_cat = p.get('x_studio_sub_categora')
    if isinstance(sub_cat, (list, tuple)) and len(sub_cat) > 1:
        sub_cat_str = sub_cat[1][:20]
    else:
        sub_cat_str = str(sub_cat)[:20] if sub_cat else 'None'
    
    print(f"{nombre:<60} {categ:<30} {sub_cat_str:<20}")

print(f"\n{'='*140}")
