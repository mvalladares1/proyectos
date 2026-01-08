"""
Debug Script: Verificar campo Manejo en productos de recepciones
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.odoo_client import OdooClient

USUARIO = os.getenv("ODOO_USER", "mvalladares@riofuturo.cl")
API_KEY = os.getenv("ODOO_API_KEY", "c0766224bec30cac071ffe43a858c9ccbd521ddd")

def main():
    print("=" * 80)
    print("DEBUG: Campo Manejo en Productos")
    print("=" * 80)
    
    odoo = OdooClient(username=USUARIO, password=API_KEY)
    print("Conexión OK\n")
    
    # 1. Buscar algunas recepciones recientes
    print("1. BUSCANDO RECEPCIONES MP RECIENTES")
    recepciones = odoo.search_read(
        'stock.picking',
        [
            ('picking_type_id', 'in', [1, 217]),
            ('x_studio_categora_de_producto', '=', 'MP'),
            ('state', '=', 'done')
        ],
        ['id', 'name', 'scheduled_date'],
        limit=5,
        order='scheduled_date desc'
    )
    
    print(f"   Encontradas: {len(recepciones)}")
    for r in recepciones:
        print(f"   - {r['name']} ({r['scheduled_date']})")
    
    if not recepciones:
        print("   No hay recepciones")
        return
    
    picking_ids = [r['id'] for r in recepciones]
    
    # 2. Obtener movimientos
    print("\n2. MOVIMIENTOS DE ESAS RECEPCIONES")
    moves = odoo.search_read(
        'stock.move',
        [('picking_id', 'in', picking_ids)],
        ['picking_id', 'product_id'],
        limit=20
    )
    
    product_ids = list(set(m['product_id'][0] for m in moves if m.get('product_id')))
    print(f"   Productos únicos: {len(product_ids)}")
    
    # 3. Obtener product.product
    print("\n3. DATOS DE PRODUCT.PRODUCT")
    products = odoo.read('product.product', product_ids, ['id', 'name', 'product_tmpl_id', 'categ_id'])
    
    template_ids = list(set(p['product_tmpl_id'][0] for p in products if p.get('product_tmpl_id')))
    
    # 4. Obtener product.template con campo manejo
    print("\n4. DATOS DE PRODUCT.TEMPLATE (incluyendo x_studio_categora_tipo_de_manejo)")
    templates = odoo.read(
        'product.template',
        template_ids,
        ['id', 'name', 'x_studio_categora_tipo_de_manejo', 'x_studio_sub_categora']
    )
    
    print(f"\n   VALORES DEL CAMPO MANEJO:")
    print("   " + "-" * 70)
    
    for t in templates[:10]:
        manejo_raw = t.get('x_studio_categora_tipo_de_manejo', 'N/A')
        tipo_fruta_raw = t.get('x_studio_sub_categora', 'N/A')
        
        print(f"   Producto: {t['name'][:40]}")
        print(f"   → x_studio_categora_tipo_de_manejo: '{manejo_raw}' (tipo: {type(manejo_raw).__name__})")
        print(f"   → x_studio_sub_categora: '{tipo_fruta_raw}'")
        print()
    
    print("=" * 80)

if __name__ == "__main__":
    main()
