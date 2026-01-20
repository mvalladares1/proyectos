"""
Investigar dónde están los campos de tipo y manejo en las recepciones
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.odoo_client import OdooClient

def investigar_campos():
    username = input("Usuario Odoo: ")
    password = input("API Key: ")
    
    odoo = OdooClient(username=username, password=password)
    
    fecha_desde = "2024-12-01"
    fecha_hasta = "2025-01-31"
    
    print("\n" + "="*80)
    print(f"INVESTIGAR CAMPOS EN RECEPCIONES")
    print(f"Período: {fecha_desde} → {fecha_hasta}")
    print("="*80)
    
    # =========================================================================
    # 1. OBTENER UNA RECEPCIÓN DE EJEMPLO
    # =========================================================================
    print("\n1️⃣  OBTENER RECEPCIÓN DE EJEMPLO")
    print("-" * 80)
    
    recepciones = odoo.search_read(
        'stock.picking',
        [
            ['picking_type_id.code', '=', 'incoming'],
            ['state', '=', 'done'],
            ['scheduled_date', '>=', fecha_desde],
            ['scheduled_date', '<=', fecha_hasta]
        ],
        [],  # Todos los campos
        limit=1
    )
    
    if recepciones:
        print(f"Campos en stock.picking:")
        for key in sorted(recepciones[0].keys()):
            if 'studio' in key.lower() or 'categ' in key.lower() or 'tipo' in key.lower() or 'manejo' in key.lower():
                print(f"  ✓ {key}: {recepciones[0][key]}")
    
    # =========================================================================
    # 2. OBTENER MOVIMIENTO DE STOCK DE EJEMPLO
    # =========================================================================
    print("\n2️⃣  OBTENER MOVIMIENTO DE STOCK DE EJEMPLO")
    print("-" * 80)
    
    picking_id = recepciones[0]['id']
    
    movimientos = odoo.search_read(
        'stock.move',
        [
            ['picking_id', '=', picking_id],
            ['state', '=', 'done']
        ],
        [],  # Todos los campos
        limit=1
    )
    
    if movimientos:
        print(f"\nCampos en stock.move:")
        campos_relevantes = []
        for key in sorted(movimientos[0].keys()):
            if 'studio' in key.lower() or 'categ' in key.lower() or 'tipo' in key.lower() or 'manejo' in key.lower():
                print(f"  ✓ {key}: {movimientos[0][key]}")
                campos_relevantes.append(key)
    
    # =========================================================================
    # 3. OBTENER STOCK.MOVE.LINE DE EJEMPLO
    # =========================================================================
    print("\n3️⃣  OBTENER STOCK.MOVE.LINE DE EJEMPLO")
    print("-" * 80)
    
    move_id = movimientos[0]['id']
    
    move_lines = odoo.search_read(
        'stock.move.line',
        [['move_id', '=', move_id]],
        [],  # Todos los campos
        limit=1
    )
    
    if move_lines:
        print(f"\nCampos en stock.move.line:")
        for key in sorted(move_lines[0].keys()):
            if 'studio' in key.lower() or 'categ' in key.lower() or 'tipo' in key.lower() or 'manejo' in key.lower():
                print(f"  ✓ {key}: {move_lines[0][key]}")
    
    # =========================================================================
    # 4. OBTENER PRODUCTO COMPLETO
    # =========================================================================
    print("\n4️⃣  OBTENER PRODUCTO COMPLETO")
    print("-" * 80)
    
    prod_id = movimientos[0]['product_id'][0]
    
    producto = odoo.search_read(
        'product.product',
        [['id', '=', prod_id]],
        [],  # Todos los campos
        limit=1
    )
    
    if producto:
        print(f"\nProducto: {producto[0].get('name', 'N/A')}")
        print(f"\nCampos studio/tipo/manejo/categ en product.product:")
        for key in sorted(producto[0].keys()):
            if 'studio' in key.lower() or 'categ' in key.lower() or 'tipo' in key.lower() or 'manejo' in key.lower():
                valor = producto[0][key]
                print(f"  ✓ {key}: {valor}")
    
    # =========================================================================
    # 5. ANALIZAR TODOS LOS MOVIMIENTOS
    # =========================================================================
    print("\n5️⃣  ANALIZAR TODOS LOS MOVIMIENTOS CON CAMPOS")
    print("-" * 80)
    
    # Obtener todos los movimientos del período
    all_picking = odoo.search_read(
        'stock.picking',
        [
            ['picking_type_id.code', '=', 'incoming'],
            ['state', '=', 'done'],
            ['scheduled_date', '>=', fecha_desde],
            ['scheduled_date', '<=', fecha_hasta]
        ],
        ['id'],
        limit=10000
    )
    
    picking_ids = [p['id'] for p in all_picking]
    print(f"Total recepciones: {len(picking_ids)}")
    
    # Campos a buscar en stock.move (SIN los campos de producto)
    campos_a_leer = [
        'product_id', 
        'product_uom_qty', 
        'picking_id'
    ]
    
    print(f"Leyendo movimientos...")
    
    all_moves = odoo.search_read(
        'stock.move',
        [
            ['picking_id', 'in', picking_ids],
            ['state', '=', 'done']
        ],
        campos_a_leer,
        limit=100000
    )
    
    print(f"Total movimientos: {len(all_moves)}")
    total_kg = sum(m.get('product_uom_qty', 0) for m in all_moves)
    print(f"Total kg: {total_kg:,.2f}")
    
    # Obtener productos únicos
    prod_ids_moves = list(set([m.get('product_id', [None])[0] for m in all_moves if m.get('product_id')]))
    print(f"\nProductos únicos en movimientos: {len(prod_ids_moves)}")
    
    # Obtener información de productos con categoría MP
    print(f"Obteniendo info de productos...")
    productos_todos = odoo.search_read(
        'product.product',
        [['id', 'in', prod_ids_moves]],
        ['id', 'name', 'categ_id', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
        limit=10000
    )
    
    # Mapear productos
    productos_map = {}
    con_tipo = 0
    con_manejo = 0
    con_ambos = 0
    es_mp_count = 0
    
    for prod in productos_todos:
        tipo = prod.get('x_studio_sub_categora')
        manejo = prod.get('x_studio_categora_tipo_de_manejo')
        categ = prod.get('categ_id', [None, 'N/A'])
        categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
        
        tiene_tipo = False
        tiene_manejo = False
        
        if tipo:
            if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
                tiene_tipo = True
                tipo_str = tipo[1]
            elif isinstance(tipo, str) and tipo:
                tiene_tipo = True
                tipo_str = tipo
            else:
                tipo_str = None
        else:
            tipo_str = None
        
        if manejo:
            if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
                tiene_manejo = True
                manejo_str = manejo[1]
            elif isinstance(manejo, str) and manejo:
                tiene_manejo = True
                manejo_str = manejo
            else:
                manejo_str = None
        else:
            manejo_str = None
        
        es_mp = 'PRODUCTOS / MP' in categ_name or 'PRODUCTOS / PTT' in categ_name or 'PRODUCTOS / PSP' in categ_name
        
        if tiene_tipo:
            con_tipo += 1
        if tiene_manejo:
            con_manejo += 1
        if tiene_tipo and tiene_manejo:
            con_ambos += 1
        if es_mp:
            es_mp_count += 1
        
        productos_map[prod['id']] = {
            'nombre': prod.get('name', ''),
            'tipo': tipo_str,
            'manejo': manejo_str,
            'tiene_tipo': tiene_tipo,
            'tiene_manejo': tiene_manejo,
            'tiene_ambos': tiene_tipo and tiene_manejo,
            'es_mp': es_mp,
            'categoria': categ_name
        }
    
    print(f"\nProductos con x_studio_sub_categora: {con_tipo}")
    print(f"Productos con x_studio_categora_tipo_de_manejo: {con_manejo}")
    print(f"Productos con AMBOS campos: {con_ambos}")
    print(f"Productos categoría MP/PTT/PSP: {es_mp_count}")
    
    # Calcular kg por categoría
    kg_con_tipo = 0
    kg_con_manejo = 0
    kg_con_ambos = 0
    kg_mp = 0
    kg_mp_con_ambos = 0
    
    for move in all_moves:
        prod_id = move.get('product_id', [None])[0]
        if prod_id in productos_map:
            kg = move.get('product_uom_qty', 0)
            prod_info = productos_map[prod_id]
            
            if prod_info['tiene_tipo']:
                kg_con_tipo += kg
            if prod_info['tiene_manejo']:
                kg_con_manejo += kg
            if prod_info['tiene_ambos']:
                kg_con_ambos += kg
            if prod_info['es_mp']:
                kg_mp += kg
                if prod_info['tiene_ambos']:
                    kg_mp_con_ambos += kg
    
    print(f"\nKg con tipo de fruta: {kg_con_tipo:,.2f}")
    print(f"Kg con manejo: {kg_con_manejo:,.2f}")
    print(f"Kg con AMBOS campos: {kg_con_ambos:,.2f}")
    print(f"Kg de productos MP: {kg_mp:,.2f}")
    print(f"Kg de MP con tipo+manejo: {kg_mp_con_ambos:,.2f}")
    
    # Top productos MP sin tipo/manejo
    print(f"\n📋 TOP 10 PRODUCTOS MP SIN TIPO/MANEJO:")
    print("-" * 80)
    
    mp_sin_campos = {}
    for move in all_moves:
        prod_id = move.get('product_id', [None])[0]
        if prod_id in productos_map:
            prod_info = productos_map[prod_id]
            if prod_info['es_mp'] and not prod_info['tiene_ambos']:
                if prod_id not in mp_sin_campos:
                    mp_sin_campos[prod_id] = {
                        'nombre': prod_info['nombre'],
                        'categoria': prod_info['categoria'],
                        'tipo': prod_info['tipo'],
                        'manejo': prod_info['manejo'],
                        'kg': 0
                    }
                mp_sin_campos[prod_id]['kg'] += move.get('product_uom_qty', 0)
    
    top_mp_sin = sorted(mp_sin_campos.items(), key=lambda x: x[1]['kg'], reverse=True)[:10]
    
    for i, (prod_id, data) in enumerate(top_mp_sin, 1):
        print(f"{i:2d}. {data['nombre'][:60]}")
        print(f"    Categoría: {data['categoria']}")
        print(f"    Tipo: {data['tipo'] or 'NO TIENE'} | Manejo: {data['manejo'] or 'NO TIENE'}")
        print(f"    Kg: {data['kg']:,.2f}")
        print()
    
    print("\n" + "="*80)
    print(f"CONCLUSIÓN:")
    print(f"  Total kg en período: {total_kg:,.2f}")
    print(f"  Kg productos MP: {kg_mp:,.2f} ({kg_mp/total_kg*100:.1f}%)")
    print(f"  Kg MP con tipo+manejo: {kg_mp_con_ambos:,.2f} ({kg_mp_con_ambos/kg_mp*100:.1f}% del MP)")
    print(f"  Kg MP SIN tipo+manejo: {kg_mp - kg_mp_con_ambos:,.2f} ({(kg_mp - kg_mp_con_ambos)/kg_mp*100:.1f}% del MP)")
    print("="*80)

if __name__ == "__main__":
    investigar_campos()
