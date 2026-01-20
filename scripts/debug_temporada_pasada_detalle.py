"""
Script de debug detallado para temporada pasada
Objetivo: Entender los 4.5M kg recepcionados vs 2.4M kg mostrados en dashboard
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.odoo_client import OdooClient

def debug_temporada_pasada():
    """Analiza en detalle la temporada Nov 2024 - Ene 2025."""
    
    username = input("Usuario Odoo: ")
    password = input("API Key: ")
    
    odoo = OdooClient(username=username, password=password)
    
    fecha_desde = "2024-11-01"
    fecha_hasta = "2025-01-31"
    
    print("\n" + "="*80)
    print(f"ANÁLISIS DETALLADO: {fecha_desde} → {fecha_hasta}")
    print("="*80)
    
    # =========================================================================
    # 1. RECEPCIONES
    # =========================================================================
    print("\n1️⃣  RECEPCIONES (stock.picking)")
    print("-" * 80)
    
    recepciones = odoo.search_read(
        'stock.picking',
        [
            ['picking_type_id.code', '=', 'incoming'],
            ['state', '=', 'done'],
            ['scheduled_date', '>=', fecha_desde],
            ['scheduled_date', '<=', fecha_hasta]
        ],
        ['name', 'scheduled_date', 'origin', 'location_dest_id'],
        limit=10000
    )
    
    print(f"Total recepciones: {len(recepciones)}")
    
    # Ver ubicaciones de destino
    ubicaciones = {}
    for rec in recepciones:
        loc = rec.get('location_dest_id', [None, 'N/A'])
        loc_name = loc[1] if isinstance(loc, (list, tuple)) else str(loc)
        ubicaciones[loc_name] = ubicaciones.get(loc_name, 0) + 1
    
    print(f"\nDistribución por ubicación de destino:")
    for loc, count in sorted(ubicaciones.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {loc}: {count} recepciones")
    
    # =========================================================================
    # 2. MOVIMIENTOS DE STOCK
    # =========================================================================
    print("\n2️⃣  MOVIMIENTOS DE STOCK")
    print("-" * 80)
    
    picking_ids = [r['id'] for r in recepciones]
    
    movimientos = odoo.search_read(
        'stock.move',
        [
            ['picking_id', 'in', picking_ids],
            ['state', '=', 'done']
        ],
        ['product_id', 'product_uom_qty', 'picking_id', 'location_dest_id', 'reference'],
        limit=100000
    )
    
    print(f"Total movimientos: {len(movimientos)}")
    total_kg = sum(m.get('product_uom_qty', 0) for m in movimientos)
    print(f"Total kg: {total_kg:,.2f}")
    
    # Ver ubicaciones de destino en movimientos
    ubicaciones_mov = {}
    for mov in movimientos:
        loc = mov.get('location_dest_id', [None, 'N/A'])
        loc_name = loc[1] if isinstance(loc, (list, tuple)) else str(loc)
        ubicaciones_mov[loc_name] = ubicaciones_mov.get(loc_name, {
            'count': 0,
            'kg': 0
        })
        ubicaciones_mov[loc_name]['count'] += 1
        ubicaciones_mov[loc_name]['kg'] += mov.get('product_uom_qty', 0)
    
    print(f"\nDistribución de kg por ubicación de destino:")
    for loc, stats in sorted(ubicaciones_mov.items(), key=lambda x: x[1]['kg'], reverse=True)[:15]:
        print(f"  {loc}: {stats['kg']:,.2f} kg ({stats['count']} movimientos)")
    
    # =========================================================================
    # 3. FILTRAR SOLO MOVIMIENTOS A UBICACIONES PRODUCTIVAS
    # =========================================================================
    print("\n3️⃣  FILTRAR UBICACIONES PRODUCTIVAS")
    print("-" * 80)
    
    # Ubicaciones que probablemente son de producción/almacén
    ubicaciones_productivas = [
        'RFP', 'VILKUN', 'SAN JOSE', 'WH/Stock', 'Stock', 'Inventario',
        'MATERIA PRIMA', 'PRODUCCIÓN', 'ALMACÉN'
    ]
    
    movimientos_productivos = []
    for mov in movimientos:
        loc = mov.get('location_dest_id', [None, 'N/A'])
        loc_name = loc[1] if isinstance(loc, (list, tuple)) else str(loc)
        
        # Verificar si la ubicación contiene alguna palabra clave
        es_productiva = any(palabra in loc_name.upper() for palabra in ubicaciones_productivas)
        
        if es_productiva:
            movimientos_productivos.append(mov)
    
    total_kg_productivos = sum(m.get('product_uom_qty', 0) for m in movimientos_productivos)
    print(f"Movimientos a ubicaciones productivas: {len(movimientos_productivos)}")
    print(f"Total kg productivos: {total_kg_productivos:,.2f}")
    print(f"% del total: {total_kg_productivos/total_kg*100:.1f}%")
    
    # =========================================================================
    # 4. ANALIZAR PRODUCTOS
    # =========================================================================
    print("\n4️⃣  ANÁLISIS DE PRODUCTOS")
    print("-" * 80)
    
    # Usar todos los movimientos primero
    prod_ids = list(set([m.get('product_id', [None])[0] for m in movimientos if m.get('product_id')]))
    
    print(f"Productos únicos (todos): {len(prod_ids)}")
    
    productos = odoo.search_read(
        'product.product',
        [['id', 'in', prod_ids]],
        ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo', 'categ_id'],
        limit=10000
    )
    
    # Clasificar productos
    productos_map = {}
    con_tipo_manejo = 0
    sin_tipo = 0
    sin_manejo = 0
    
    for prod in productos:
        tipo = prod.get('x_studio_sub_categora')
        manejo = prod.get('x_studio_categora_tipo_de_manejo')
        categ = prod.get('categ_id', [None, 'N/A'])
        categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
        
        if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
            tipo_str = tipo[1]
        elif isinstance(tipo, str) and tipo:
            tipo_str = tipo
        else:
            tipo_str = None
        
        if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
            manejo_str = manejo[1]
        elif isinstance(manejo, str) and manejo:
            manejo_str = manejo
        else:
            manejo_str = None
        
        tiene_ambos = bool(tipo_str and manejo_str)
        
        if tiene_ambos:
            con_tipo_manejo += 1
        if not tipo_str:
            sin_tipo += 1
        if not manejo_str:
            sin_manejo += 1
        
        productos_map[prod['id']] = {
            'nombre': prod.get('name', ''),
            'tipo': tipo_str,
            'manejo': manejo_str,
            'tiene_ambos': tiene_ambos,
            'categoria': categ_name
        }
    
    print(f"Productos con tipo Y manejo: {con_tipo_manejo} ({con_tipo_manejo/len(productos)*100:.1f}%)")
    print(f"Productos sin tipo: {sin_tipo}")
    print(f"Productos sin manejo: {sin_manejo}")
    
    # =========================================================================
    # 5. CALCULAR KG POR CATEGORÍA
    # =========================================================================
    print("\n5️⃣  KG POR CATEGORÍA DE PRODUCTO")
    print("-" * 80)
    
    stats = {
        'con_tipo_manejo': {'kg': 0, 'movs': 0},
        'sin_tipo_manejo': {'kg': 0, 'movs': 0}
    }
    
    productos_sin_tipo_stats = {}
    
    for mov in movimientos:
        prod_id = mov.get('product_id', [None])[0]
        if prod_id in productos_map:
            kg = mov.get('product_uom_qty', 0)
            
            if productos_map[prod_id]['tiene_ambos']:
                stats['con_tipo_manejo']['kg'] += kg
                stats['con_tipo_manejo']['movs'] += 1
            else:
                stats['sin_tipo_manejo']['kg'] += kg
                stats['sin_tipo_manejo']['movs'] += 1
                
                # Acumular stats de productos sin tipo/manejo
                if prod_id not in productos_sin_tipo_stats:
                    productos_sin_tipo_stats[prod_id] = {
                        'nombre': productos_map[prod_id]['nombre'],
                        'categoria': productos_map[prod_id]['categoria'],
                        'kg': 0
                    }
                productos_sin_tipo_stats[prod_id]['kg'] += kg
    
    print(f"CON tipo y manejo:")
    print(f"  Kg: {stats['con_tipo_manejo']['kg']:,.2f}")
    print(f"  Movimientos: {stats['con_tipo_manejo']['movs']}")
    
    print(f"\nSIN tipo o manejo:")
    print(f"  Kg: {stats['sin_tipo_manejo']['kg']:,.2f}")
    print(f"  Movimientos: {stats['sin_tipo_manejo']['movs']}")
    print(f"  % del total: {stats['sin_tipo_manejo']['kg']/total_kg*100:.1f}%")
    
    # =========================================================================
    # 6. TOP PRODUCTOS SIN TIPO/MANEJO
    # =========================================================================
    print("\n6️⃣  TOP 20 PRODUCTOS SIN TIPO/MANEJO (por kg)")
    print("-" * 80)
    
    top_sin_tipo = sorted(productos_sin_tipo_stats.items(), key=lambda x: x[1]['kg'], reverse=True)[:20]
    
    for i, (prod_id, stats) in enumerate(top_sin_tipo, 1):
        print(f"{i:2d}. {stats['nombre'][:50]:<50} | {stats['kg']:>12,.2f} kg")
        print(f"    Categoría: {stats['categoria']}")
    
    # =========================================================================
    # RESUMEN FINAL
    # =========================================================================
    print("\n" + "="*80)
    print("RESUMEN")
    print("="*80)
    print(f"Total recepciones: {len(recepciones)}")
    print(f"Total movimientos: {len(movimientos)}")
    print(f"Total kg (TODOS los movimientos): {total_kg:,.2f}")
    print(f"Total kg (ubicaciones productivas): {total_kg_productivos:,.2f}")
    print(f"")
    print(f"Kg CON tipo y manejo: {stats['con_tipo_manejo']['kg']:,.2f} ({stats['con_tipo_manejo']['kg']/total_kg*100:.1f}%)")
    print(f"Kg SIN tipo o manejo: {stats['sin_tipo_manejo']['kg']:,.2f} ({stats['sin_tipo_manejo']['kg']/total_kg*100:.1f}%)")
    print("="*80)
    
    print("\n💡 POSIBLE EXPLICACIÓN:")
    if stats['sin_tipo_manejo']['kg'] > stats['con_tipo_manejo']['kg']:
        print("   La mayoría de los kg recepcionados NO tienen tipo/manejo asignado.")
        print("   Revisar si son productos de materia prima o insumos/materiales.")
    
    if total_kg > total_kg_productivos * 1.5:
        print("   Hay muchos movimientos a ubicaciones no productivas.")
        print("   Podrían ser devoluciones, ajustes o movimientos internos.")

if __name__ == "__main__":
    debug_temporada_pasada()
