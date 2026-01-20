"""
Script para calcular compras de MATERIA PRIMA (fruta) en temporada 2024-2025
Objetivo: Ver cuánto se compró realmente de fruta, no insumos
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.odoo_client import OdooClient

def debug_compras_mp_temporada():
    """Analiza solo compras de materia prima (fruta)."""
    
    username = input("Usuario Odoo: ")
    password = input("API Key: ")
    
    odoo = OdooClient(username=username, password=password)
    
    fecha_desde = "2024-11-01"
    fecha_hasta = "2025-01-31"
    
    print("\n" + "="*80)
    print(f"COMPRAS DE MATERIA PRIMA (FRUTA): {fecha_desde} → {fecha_hasta}")
    print("="*80)
    
    # =========================================================================
    # 1. TODAS LAS FACTURAS DE COMPRA
    # =========================================================================
    print("\n1️⃣  FACTURAS DE COMPRA")
    print("-" * 80)
    
    facturas = odoo.search_read(
        'account.move',
        [
            ['move_type', '=', 'in_invoice'],
            ['state', '=', 'posted'],
            ['invoice_date', '>=', fecha_desde],
            ['invoice_date', '<=', fecha_hasta]
        ],
        ['name', 'invoice_date', 'amount_total'],
        limit=10000
    )
    
    print(f"Total facturas: {len(facturas)}")
    total_monto_facturas = sum(f.get('amount_total', 0) for f in facturas)
    print(f"Monto total: ${total_monto_facturas:,.2f}")
    
    # =========================================================================
    # 2. LÍNEAS DE FACTURAS CON PRODUCTO
    # =========================================================================
    print("\n2️⃣  LÍNEAS DE FACTURAS CON PRODUCTO")
    print("-" * 80)
    
    factura_ids = [f['id'] for f in facturas]
    
    lineas = odoo.search_read(
        'account.move.line',
        [
            ['move_id', 'in', factura_ids],
            ['product_id', '!=', False],
            ['quantity', '>', 0],
            ['debit', '>', 0]
        ],
        ['product_id', 'quantity', 'debit', 'account_id'],
        limit=100000
    )
    
    print(f"Total líneas con producto: {len(lineas)}")
    total_kg_lineas = sum(l.get('quantity', 0) for l in lineas)
    total_debit = sum(l.get('debit', 0) for l in lineas)
    print(f"Total kg: {total_kg_lineas:,.2f}")
    print(f"Total monto (debit): ${total_debit:,.2f}")
    
    # =========================================================================
    # 3. OBTENER PRODUCTOS Y FILTRAR POR CATEGORÍA
    # =========================================================================
    print("\n3️⃣  FILTRAR POR CATEGORÍA DE PRODUCTO")
    print("-" * 80)
    
    prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas if l.get('product_id')]))
    
    productos = odoo.search_read(
        'product.product',
        [['id', 'in', prod_ids]],
        ['id', 'name', 'categ_id', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
        limit=10000
    )
    
    print(f"Productos únicos: {len(productos)}")
    
    # Clasificar por categoría
    categorias_stats = {}
    productos_map = {}
    
    for prod in productos:
        categ = prod.get('categ_id', [None, 'N/A'])
        categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
        
        # Normalizar tipo y manejo
        tipo = prod.get('x_studio_sub_categora')
        manejo = prod.get('x_studio_categora_tipo_de_manejo')
        
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
        
        # Determinar si es MP (Materia Prima)
        es_mp = 'PRODUCTOS / MP' in categ_name or 'PRODUCTOS / PTT' in categ_name or 'PRODUCTOS / PSP' in categ_name
        
        productos_map[prod['id']] = {
            'nombre': prod.get('name', ''),
            'categoria': categ_name,
            'es_mp': es_mp,
            'tipo': tipo_str,
            'manejo': manejo_str,
            'tiene_tipo_manejo': bool(tipo_str and manejo_str)
        }
        
        if categ_name not in categorias_stats:
            categorias_stats[categ_name] = {
                'productos': 0,
                'kg': 0,
                'monto': 0
            }
        categorias_stats[categ_name]['productos'] += 1
    
    # =========================================================================
    # 4. CALCULAR KG Y MONTO POR CATEGORÍA
    # =========================================================================
    print("\n4️⃣  COMPRAS POR CATEGORÍA")
    print("-" * 80)
    
    for linea in lineas:
        prod_id = linea.get('product_id', [None])[0]
        if prod_id in productos_map:
            categ = productos_map[prod_id]['categoria']
            categorias_stats[categ]['kg'] += linea.get('quantity', 0)
            categorias_stats[categ]['monto'] += linea.get('debit', 0)
    
    # Ordenar por monto
    categorias_ordenadas = sorted(categorias_stats.items(), key=lambda x: x[1]['monto'], reverse=True)
    
    for categ, stats in categorias_ordenadas[:20]:
        print(f"{categ}")
        print(f"  Productos: {stats['productos']}")
        print(f"  Kg: {stats['kg']:,.2f}")
        print(f"  Monto: ${stats['monto']:,.2f}")
        print()
    
    # =========================================================================
    # 5. TOTALES SOLO MATERIA PRIMA
    # =========================================================================
    print("\n5️⃣  TOTALES DE MATERIA PRIMA (FRUTA)")
    print("="*80)
    
    kg_mp = 0
    monto_mp = 0
    kg_mp_con_tipo_manejo = 0
    monto_mp_con_tipo_manejo = 0
    kg_mp_sin_tipo_manejo = 0
    monto_mp_sin_tipo_manejo = 0
    
    productos_mp_sin_tipo = {}
    
    for linea in lineas:
        prod_id = linea.get('product_id', [None])[0]
        if prod_id in productos_map and productos_map[prod_id]['es_mp']:
            kg = linea.get('quantity', 0)
            monto = linea.get('debit', 0)
            
            kg_mp += kg
            monto_mp += monto
            
            if productos_map[prod_id]['tiene_tipo_manejo']:
                kg_mp_con_tipo_manejo += kg
                monto_mp_con_tipo_manejo += monto
            else:
                kg_mp_sin_tipo_manejo += kg
                monto_mp_sin_tipo_manejo += monto
                
                # Acumular productos sin tipo/manejo
                if prod_id not in productos_mp_sin_tipo:
                    productos_mp_sin_tipo[prod_id] = {
                        'nombre': productos_map[prod_id]['nombre'],
                        'kg': 0,
                        'monto': 0
                    }
                productos_mp_sin_tipo[prod_id]['kg'] += kg
                productos_mp_sin_tipo[prod_id]['monto'] += monto
    
    print(f"TOTAL MATERIA PRIMA (FRUTA):")
    print(f"  Kg: {kg_mp:,.2f}")
    print(f"  Monto: ${monto_mp:,.2f}")
    print(f"  Precio promedio: ${monto_mp/kg_mp:,.2f}/kg" if kg_mp > 0 else "  N/A")
    
    print(f"\nCON tipo y manejo:")
    print(f"  Kg: {kg_mp_con_tipo_manejo:,.2f} ({kg_mp_con_tipo_manejo/kg_mp*100:.1f}%)")
    print(f"  Monto: ${monto_mp_con_tipo_manejo:,.2f}")
    
    print(f"\nSIN tipo o manejo:")
    print(f"  Kg: {kg_mp_sin_tipo_manejo:,.2f} ({kg_mp_sin_tipo_manejo/kg_mp*100:.1f}%)")
    print(f"  Monto: ${monto_mp_sin_tipo_manejo:,.2f}")
    
    # =========================================================================
    # 6. PRODUCTOS MP SIN TIPO/MANEJO
    # =========================================================================
    print("\n6️⃣  TOP 15 PRODUCTOS MP SIN TIPO/MANEJO")
    print("-" * 80)
    
    top_mp_sin_tipo = sorted(productos_mp_sin_tipo.items(), key=lambda x: x[1]['kg'], reverse=True)[:15]
    
    for i, (prod_id, stats) in enumerate(top_mp_sin_tipo, 1):
        print(f"{i:2d}. {stats['nombre'][:60]}")
        print(f"    Kg: {stats['kg']:>12,.2f} | Monto: ${stats['monto']:>15,.2f}")
    
    # =========================================================================
    # RESUMEN FINAL
    # =========================================================================
    print("\n" + "="*80)
    print("RESUMEN COMPRAS TEMPORADA 2024-2025")
    print("="*80)
    print(f"Todas las facturas: ${total_monto_facturas:,.2f}")
    print(f"Todas las líneas con producto: {total_kg_lineas:,.2f} kg (${total_debit:,.2f})")
    print(f"")
    print(f"SOLO MATERIA PRIMA (FRUTA):")
    print(f"  Total: {kg_mp:,.2f} kg (${monto_mp:,.2f})")
    print(f"  Con tipo+manejo: {kg_mp_con_tipo_manejo:,.2f} kg ({kg_mp_con_tipo_manejo/kg_mp*100:.1f}%)")
    print(f"  Sin tipo+manejo: {kg_mp_sin_tipo_manejo:,.2f} kg ({kg_mp_sin_tipo_manejo/kg_mp*100:.1f}%)")
    print("="*80)
    
    print("\n💡 CONCLUSIÓN:")
    print(f"   Se compraron {kg_mp:,.0f} kg de fruta por ${monto_mp:,.0f}")
    print(f"   Precio promedio: ${monto_mp/kg_mp:,.2f}/kg")
    if kg_mp_sin_tipo_manejo > kg_mp_con_tipo_manejo:
        print(f"   ⚠️  {kg_mp_sin_tipo_manejo/kg_mp*100:.0f}% de la fruta NO tiene tipo/manejo asignado")
        print(f"   Esto representa {kg_mp_sin_tipo_manejo:,.0f} kg que no aparecen en el análisis")

if __name__ == "__main__":
    debug_compras_mp_temporada()
