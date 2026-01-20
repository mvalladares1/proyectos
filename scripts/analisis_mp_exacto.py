"""
Script para analizar exactamente como lo hace el usuario en Odoo
Rango: 01/12/2024 hasta 31/01/2025
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.odoo_client import OdooClient

def analisis_exacto():
    username = input("Usuario Odoo: ")
    password = input("API Key: ")
    
    odoo = OdooClient(username=username, password=password)
    
    # Rango EXACTO como el usuario
    fecha_desde = "2024-12-01"
    fecha_hasta = "2025-01-31"
    
    print("\n" + "="*80)
    print(f"ANÁLISIS EXACTO: {fecha_desde} hasta {fecha_hasta}")
    print("="*80)
    
    # Buscar recepciones de tipo "incoming" en estado "done"
    print("\n📦 RECEPCIONES...")
    recepciones = odoo.search_read(
        'stock.picking',
        [
            ['picking_type_id.code', '=', 'incoming'],
            ['state', '=', 'done'],
            ['scheduled_date', '>=', fecha_desde + ' 00:00:00'],
            ['scheduled_date', '<=', fecha_hasta + ' 23:59:59']
        ],
        ['id', 'name', 'scheduled_date'],
        limit=10000
    )
    
    print(f"Total recepciones: {len(recepciones)}")
    
    picking_ids = [r['id'] for r in recepciones]
    
    # Obtener movimientos
    print("\n📋 MOVIMIENTOS DE STOCK...")
    movimientos = odoo.search_read(
        'stock.move',
        [
            ['picking_id', 'in', picking_ids],
            ['state', '=', 'done']
        ],
        ['id', 'product_id', 'product_uom_qty', 'picking_id'],
        limit=100000
    )
    
    print(f"Total movimientos: {len(movimientos)}")
    total_kg = sum(m.get('product_uom_qty', 0) for m in movimientos)
    print(f"Total kg: {total_kg:,.2f}")
    
    # Productos únicos
    prod_ids = list(set([m.get('product_id', [None])[0] for m in movimientos if m.get('product_id')]))
    
    print(f"\n🍓 PRODUCTOS...")
    print(f"Productos únicos: {len(prod_ids)}")
    
    # Obtener info de productos
    productos = odoo.search_read(
        'product.product',
        [['id', 'in', prod_ids]],
        ['id', 'name', 'categ_id', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
        limit=10000
    )
    
    # Categorizar productos
    productos_map = {}
    stats = {
        'total': 0,
        'con_tipo': 0,
        'con_manejo': 0,
        'con_ambos': 0,
        'mp': 0,
        'mp_con_ambos': 0
    }
    
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
        
        tiene_ambos = tiene_tipo and tiene_manejo
        es_mp = 'PRODUCTOS / MP' in categ_name or 'PRODUCTOS / PTT' in categ_name or 'PRODUCTOS / PSP' in categ_name
        
        stats['total'] += 1
        if tiene_tipo:
            stats['con_tipo'] += 1
        if tiene_manejo:
            stats['con_manejo'] += 1
        if tiene_ambos:
            stats['con_ambos'] += 1
        if es_mp:
            stats['mp'] += 1
            if tiene_ambos:
                stats['mp_con_ambos'] += 1
        
        productos_map[prod['id']] = {
            'nombre': prod.get('name', ''),
            'tipo': tipo_str,
            'manejo': manejo_str,
            'tiene_tipo': tiene_tipo,
            'tiene_manejo': tiene_manejo,
            'tiene_ambos': tiene_ambos,
            'es_mp': es_mp,
            'categoria': categ_name
        }
    
    print(f"\nEstadísticas productos:")
    print(f"  Total: {stats['total']}")
    print(f"  Con tipo: {stats['con_tipo']}")
    print(f"  Con manejo: {stats['con_manejo']}")
    print(f"  Con AMBOS: {stats['con_ambos']}")
    print(f"  Categoría MP: {stats['mp']}")
    print(f"  MP con ambos campos: {stats['mp_con_ambos']}")
    
    # Calcular kg por categoría
    kg_stats = {
        'total': 0,
        'con_tipo': 0,
        'con_manejo': 0,
        'con_ambos': 0,
        'mp': 0,
        'mp_con_ambos': 0,
        'no_mp': 0
    }
    
    productos_detalle = {}
    
    for mov in movimientos:
        prod_id = mov.get('product_id', [None])[0]
        kg = mov.get('product_uom_qty', 0)
        
        kg_stats['total'] += kg
        
        if prod_id in productos_map:
            info = productos_map[prod_id]
            
            if info['tiene_tipo']:
                kg_stats['con_tipo'] += kg
            if info['tiene_manejo']:
                kg_stats['con_manejo'] += kg
            if info['tiene_ambos']:
                kg_stats['con_ambos'] += kg
            if info['es_mp']:
                kg_stats['mp'] += kg
                if info['tiene_ambos']:
                    kg_stats['mp_con_ambos'] += kg
                
                # Detalle por producto MP
                if prod_id not in productos_detalle:
                    productos_detalle[prod_id] = {
                        'nombre': info['nombre'],
                        'tipo': info['tipo'],
                        'manejo': info['manejo'],
                        'tiene_ambos': info['tiene_ambos'],
                        'kg': 0
                    }
                productos_detalle[prod_id]['kg'] += kg
            else:
                kg_stats['no_mp'] += kg
    
    print(f"\n📊 KG POR CATEGORÍA:")
    print(f"  Total: {kg_stats['total']:,.2f} kg")
    print(f"  Con tipo: {kg_stats['con_tipo']:,.2f} kg")
    print(f"  Con manejo: {kg_stats['con_manejo']:,.2f} kg")
    print(f"  Con AMBOS: {kg_stats['con_ambos']:,.2f} kg")
    print(f"  Categoría MP: {kg_stats['mp']:,.2f} kg")
    print(f"  MP con ambos campos: {kg_stats['mp_con_ambos']:,.2f} kg")
    print(f"  NO MP: {kg_stats['no_mp']:,.2f} kg")
    
    # Productos MP
    print(f"\n🍓 TOP 20 PRODUCTOS MP:")
    print("-" * 80)
    
    top_productos = sorted(productos_detalle.items(), key=lambda x: x[1]['kg'], reverse=True)[:20]
    
    for i, (prod_id, data) in enumerate(top_productos, 1):
        tiene = "✅" if data['tiene_ambos'] else "❌"
        print(f"{i:2d}. {tiene} {data['nombre'][:55]}")
        print(f"      Tipo: {data['tipo'] or 'NO TIENE':20} | Manejo: {data['manejo'] or 'NO TIENE'}")
        print(f"      Kg: {data['kg']:>12,.2f}")
        print()
    
    print("\n" + "="*80)
    print("RESUMEN FINAL")
    print("="*80)
    print(f"Período: {fecha_desde} hasta {fecha_hasta}")
    print(f"Recepciones: {len(recepciones)}")
    print(f"Movimientos: {len(movimientos)}")
    print(f"Total kg: {kg_stats['total']:,.2f}")
    print(f"Kg MP: {kg_stats['mp']:,.2f} ({kg_stats['mp']/kg_stats['total']*100:.1f}%)")
    print(f"Kg MP con tipo+manejo: {kg_stats['mp_con_ambos']:,.2f} ({kg_stats['mp_con_ambos']/kg_stats['mp']*100:.1f}% del MP)")
    print("="*80)

if __name__ == "__main__":
    analisis_exacto()
