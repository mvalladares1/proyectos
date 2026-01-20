"""
Buscar TODOS los productos que tengan manejo, sin filtrar por categoría MP
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.odoo_client import OdooClient

def buscar_todos_con_manejo():
    username = input("Usuario Odoo: ")
    password = input("API Key: ")
    
    odoo = OdooClient(username=username, password=password)
    
    fecha_desde = "2024-12-01"
    fecha_hasta = "2025-01-31"
    
    print("\n" + "="*80)
    print(f"BUSCAR TODOS LOS PRODUCTOS CON MANEJO (sin filtrar por categoría)")
    print(f"Período: {fecha_desde} hasta {fecha_hasta}")
    print("="*80)
    
    # Recepciones
    recepciones = odoo.search_read(
        'stock.picking',
        [
            ['picking_type_id.code', '=', 'incoming'],
            ['state', '=', 'done'],
            ['scheduled_date', '>=', fecha_desde + ' 00:00:00'],
            ['scheduled_date', '<=', fecha_hasta + ' 23:59:59']
        ],
        ['id'],
        limit=10000
    )
    
    picking_ids = [r['id'] for r in recepciones]
    print(f"Recepciones: {len(recepciones)}")
    
    # Movimientos
    movimientos = odoo.search_read(
        'stock.move',
        [
            ['picking_id', 'in', picking_ids],
            ['state', '=', 'done']
        ],
        ['id', 'product_id', 'product_uom_qty'],
        limit=100000
    )
    
    print(f"Movimientos: {len(movimientos)}")
    total_kg = sum(m.get('product_uom_qty', 0) for m in movimientos)
    print(f"Total kg: {total_kg:,.2f}")
    
    # Productos
    prod_ids = list(set([m.get('product_id', [None])[0] for m in movimientos if m.get('product_id')]))
    print(f"Productos únicos: {len(prod_ids)}")
    
    productos = odoo.search_read(
        'product.product',
        [['id', 'in', prod_ids]],
        ['id', 'name', 'categ_id', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
        limit=10000
    )
    
    # Categorizar SIN filtrar por categ_id
    productos_map = {}
    con_tipo = 0
    con_manejo = 0
    con_ambos = 0
    
    for prod in productos:
        tipo = prod.get('x_studio_sub_categora')
        manejo = prod.get('x_studio_categora_tipo_de_manejo')
        categ = prod.get('categ_id', [None, 'N/A'])
        categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
        
        # Parsear tipo
        if tipo:
            if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
                tipo_str = tipo[1]
                tiene_tipo = True
            elif isinstance(tipo, str) and tipo:
                tipo_str = tipo
                tiene_tipo = True
            else:
                tipo_str = None
                tiene_tipo = False
        else:
            tipo_str = None
            tiene_tipo = False
        
        # Parsear manejo
        if manejo:
            if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
                manejo_str = manejo[1]
                tiene_manejo = True
            elif isinstance(manejo, str) and manejo:
                manejo_str = manejo
                tiene_manejo = True
            else:
                manejo_str = None
                tiene_manejo = False
        else:
            manejo_str = None
            tiene_manejo = False
        
        if tiene_tipo:
            con_tipo += 1
        if tiene_manejo:
            con_manejo += 1
        if tiene_tipo and tiene_manejo:
            con_ambos += 1
        
        productos_map[prod['id']] = {
            'nombre': prod.get('name', ''),
            'tipo': tipo_str,
            'manejo': manejo_str,
            'tiene_tipo': tiene_tipo,
            'tiene_manejo': tiene_manejo,
            'tiene_ambos': tiene_tipo and tiene_manejo,
            'categoria': categ_name
        }
    
    print(f"\n📊 PRODUCTOS:")
    print(f"  Con tipo: {con_tipo}")
    print(f"  Con manejo: {con_manejo}")
    print(f"  Con AMBOS: {con_ambos}")
    
    # Calcular kg
    kg_con_tipo = 0
    kg_con_manejo = 0
    kg_con_ambos = 0
    
    productos_detalle = {}
    
    for mov in movimientos:
        prod_id = mov.get('product_id', [None])[0]
        kg = mov.get('product_uom_qty', 0)
        
        if prod_id in productos_map:
            info = productos_map[prod_id]
            
            if info['tiene_tipo']:
                kg_con_tipo += kg
            if info['tiene_manejo']:
                kg_con_manejo += kg
            if info['tiene_ambos']:
                kg_con_ambos += kg
                
                if prod_id not in productos_detalle:
                    productos_detalle[prod_id] = {
                        'nombre': info['nombre'],
                        'tipo': info['tipo'],
                        'manejo': info['manejo'],
                        'categoria': info['categoria'],
                        'kg': 0
                    }
                productos_detalle[prod_id]['kg'] += kg
    
    print(f"\n📊 KG:")
    print(f"  Con tipo: {kg_con_tipo:,.2f}")
    print(f"  Con manejo: {kg_con_manejo:,.2f}")
    print(f"  Con AMBOS: {kg_con_ambos:,.2f}")
    
    # Top productos
    print(f"\n🍓 TODOS LOS PRODUCTOS CON TIPO+MANEJO:")
    print("-" * 80)
    
    top_productos = sorted(productos_detalle.items(), key=lambda x: x[1]['kg'], reverse=True)
    
    for i, (prod_id, data) in enumerate(top_productos, 1):
        print(f"{i:2d}. {data['nombre'][:60]}")
        print(f"      Tipo: {data['tipo']:20} | Manejo: {data['manejo']}")
        print(f"      Categoría: {data['categoria']}")
        print(f"      Kg: {data['kg']:>12,.2f}")
        print()
    
    print("\n" + "="*80)
    print("RESUMEN")
    print("="*80)
    print(f"Total kg: {total_kg:,.2f}")
    print(f"Kg con tipo+manejo: {kg_con_ambos:,.2f} ({kg_con_ambos/total_kg*100:.1f}%)")
    print(f"Kg sin clasificar: {total_kg - kg_con_ambos:,.2f}")
    print("="*80)

if __name__ == "__main__":
    buscar_todos_con_manejo()
