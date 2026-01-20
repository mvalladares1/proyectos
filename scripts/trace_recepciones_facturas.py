"""
Script para trazar la cadena: Recepciones MP → Órdenes Compra → Facturas
Objetivo: Entender qué pasa entre recepciones y facturas de fruta con tipo/manejo
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.odoo_client import OdooClient

def trace_recepciones_a_facturas():
    """Traza la cadena completa de recepciones a facturas."""
    
    username = input("Usuario Odoo: ")
    password = input("API Key: ")
    
    odoo = OdooClient(username=username, password=password)
    
    fecha_desde = "2024-11-01"
    fecha_hasta = "2025-01-31"
    
    print("\n" + "="*80)
    print(f"TRAZAR: RECEPCIONES → ÓRDENES COMPRA → FACTURAS")
    print(f"Período: {fecha_desde} → {fecha_hasta}")
    print("="*80)
    
    # =========================================================================
    # 1. RECEPCIONES DE MP
    # =========================================================================
    print("\n1️⃣  RECEPCIONES")
    print("-" * 80)
    
    recepciones = odoo.search_read(
        'stock.picking',
        [
            ['picking_type_id.code', '=', 'incoming'],
            ['state', '=', 'done'],
            ['scheduled_date', '>=', fecha_desde],
            ['scheduled_date', '<=', fecha_hasta]
        ],
        ['name', 'scheduled_date', 'origin'],
        limit=10000
    )
    
    print(f"Total recepciones: {len(recepciones)}")
    
    picking_ids = [r['id'] for r in recepciones]
    
    # =========================================================================
    # 2. MOVIMIENTOS DE STOCK
    # =========================================================================
    print("\n2️⃣  MOVIMIENTOS DE STOCK")
    print("-" * 80)
    
    movimientos = odoo.search_read(
        'stock.move',
        [
            ['picking_id', 'in', picking_ids],
            ['state', '=', 'done']
        ],
        ['product_id', 'product_uom_qty', 'picking_id', 'purchase_line_id'],
        limit=100000
    )
    
    print(f"Total movimientos: {len(movimientos)}")
    total_kg_movimientos = sum(m.get('product_uom_qty', 0) for m in movimientos)
    print(f"Total kg: {total_kg_movimientos:,.2f}")
    
    # =========================================================================
    # 3. FILTRAR PRODUCTOS CON TIPO Y MANEJO
    # =========================================================================
    print("\n3️⃣  FILTRAR PRODUCTOS CON TIPO Y MANEJO")
    print("-" * 80)
    
    prod_ids = list(set([m.get('product_id', [None])[0] for m in movimientos if m.get('product_id')]))
    
    productos = odoo.search_read(
        'product.product',
        [['id', 'in', prod_ids]],
        ['id', 'name', 'categ_id', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
        limit=10000
    )
    
    print(f"Productos únicos: {len(productos)}")
    
    # Mapear productos
    productos_map = {}
    con_tipo_manejo = 0
    
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
        es_mp = 'PRODUCTOS / MP' in categ_name or 'PRODUCTOS / PTT' in categ_name or 'PRODUCTOS / PSP' in categ_name
        
        if tiene_ambos:
            con_tipo_manejo += 1
        
        productos_map[prod['id']] = {
            'nombre': prod.get('name', ''),
            'tipo': tipo_str,
            'manejo': manejo_str,
            'tiene_tipo_manejo': tiene_ambos,
            'es_mp': es_mp,
            'categoria': categ_name
        }
    
    print(f"Productos con tipo Y manejo: {con_tipo_manejo}")
    
    # =========================================================================
    # 4. MOVIMIENTOS DE MP CON TIPO/MANEJO
    # =========================================================================
    print("\n4️⃣  MOVIMIENTOS DE MP CON TIPO/MANEJO")
    print("-" * 80)
    
    movimientos_mp = []
    kg_mp_recepcionado = 0
    purchase_line_ids_mp = []
    
    for mov in movimientos:
        prod_id = mov.get('product_id', [None])[0]
        if prod_id in productos_map and productos_map[prod_id]['tiene_tipo_manejo'] and productos_map[prod_id]['es_mp']:
            movimientos_mp.append(mov)
            kg_mp_recepcionado += mov.get('product_uom_qty', 0)
            
            purchase_line_id = mov.get('purchase_line_id')
            if purchase_line_id:
                pl_id = purchase_line_id[0] if isinstance(purchase_line_id, (list, tuple)) else purchase_line_id
                if pl_id:
                    purchase_line_ids_mp.append(pl_id)
    
    print(f"Movimientos de MP con tipo/manejo: {len(movimientos_mp)}")
    print(f"Kg recepcionados de MP: {kg_mp_recepcionado:,.2f}")
    print(f"Movimientos con purchase_line_id: {len([m for m in movimientos_mp if m.get('purchase_line_id')])}")
    
    # =========================================================================
    # 5. ÓRDENES DE COMPRA
    # =========================================================================
    print("\n5️⃣  ÓRDENES DE COMPRA")
    print("-" * 80)
    
    purchase_line_ids_mp = list(set(purchase_line_ids_mp))
    print(f"Purchase lines únicas: {len(purchase_line_ids_mp)}")
    
    if purchase_line_ids_mp:
        purchase_lines = odoo.search_read(
            'purchase.order.line',
            [['id', 'in', purchase_line_ids_mp]],
            ['order_id', 'product_id', 'product_qty', 'price_unit', 'price_subtotal'],
            limit=10000
        )
        
        print(f"Purchase lines encontradas: {len(purchase_lines)}")
        
        # Obtener órdenes de compra únicas
        po_ids = list(set([pl.get('order_id', [None])[0] for pl in purchase_lines if pl.get('order_id')]))
        print(f"Purchase orders únicas: {len(po_ids)}")
        
        if po_ids:
            purchase_orders = odoo.search_read(
                'purchase.order',
                [['id', 'in', po_ids]],
                ['name', 'partner_id', 'date_order', 'invoice_status', 'state', 'amount_total'],
                limit=10000
            )
            
            print(f"Purchase orders encontradas: {len(purchase_orders)}")
            
            # Estados de facturación
            estados = {}
            for po in purchase_orders:
                estado = po.get('invoice_status', 'N/A')
                estados[estado] = estados.get(estado, 0) + 1
            
            print(f"\nEstado de facturación:")
            for estado, count in estados.items():
                print(f"  {estado}: {count} órdenes")
            
            # Total de órdenes
            total_monto_po = sum(po.get('amount_total', 0) for po in purchase_orders)
            print(f"\nMonto total órdenes: ${total_monto_po:,.2f}")
            
            # ================================================================
            # 6. FACTURAS VINCULADAS A ESAS ÓRDENES
            # ================================================================
            print("\n6️⃣  FACTURAS VINCULADAS")
            print("-" * 80)
            
            # Buscar facturas que tengan purchase_line_id en estas órdenes
            facturas_lineas = odoo.search_read(
                'account.move.line',
                [
                    ['purchase_line_id', 'in', purchase_line_ids_mp],
                    ['move_id.move_type', '=', 'in_invoice'],
                    ['move_id.state', '=', 'posted']
                ],
                ['move_id', 'product_id', 'quantity', 'debit', 'purchase_line_id'],
                limit=100000
            )
            
            print(f"Líneas de factura vinculadas: {len(facturas_lineas)}")
            
            if facturas_lineas:
                # Calcular totales
                kg_facturado = 0
                monto_facturado = 0
                productos_facturados = {}
                
                for linea in facturas_lineas:
                    prod_id = linea.get('product_id', [None])[0]
                    if prod_id in productos_map:
                        kg = linea.get('quantity', 0)
                        monto = linea.get('debit', 0)
                        
                        kg_facturado += kg
                        monto_facturado += monto
                        
                        if prod_id not in productos_facturados:
                            productos_facturados[prod_id] = {
                                'nombre': productos_map[prod_id]['nombre'],
                                'tipo': productos_map[prod_id]['tipo'],
                                'manejo': productos_map[prod_id]['manejo'],
                                'kg': 0,
                                'monto': 0
                            }
                        productos_facturados[prod_id]['kg'] += kg
                        productos_facturados[prod_id]['monto'] += monto
                
                print(f"Kg facturados: {kg_facturado:,.2f}")
                print(f"Monto facturado: ${monto_facturado:,.2f}")
                
                # Facturas únicas
                factura_ids = list(set([l.get('move_id', [None])[0] for l in facturas_lineas if l.get('move_id')]))
                print(f"Facturas únicas: {len(factura_ids)}")
                
                if factura_ids:
                    facturas = odoo.search_read(
                        'account.move',
                        [['id', 'in', factura_ids]],
                        ['name', 'invoice_date', 'partner_id', 'amount_total', 'state'],
                        limit=10000
                    )
                    
                    # Fechas de facturas
                    facturas_en_periodo = 0
                    facturas_fuera_periodo = 0
                    
                    for factura in facturas:
                        fecha = factura.get('invoice_date', '')
                        if fecha >= fecha_desde and fecha <= fecha_hasta:
                            facturas_en_periodo += 1
                        else:
                            facturas_fuera_periodo += 1
                    
                    print(f"\nFacturas en período {fecha_desde} a {fecha_hasta}: {facturas_en_periodo}")
                    print(f"Facturas fuera del período: {facturas_fuera_periodo}")
            else:
                kg_facturado = 0
                monto_facturado = 0
                productos_facturados = {}
    else:
        kg_facturado = 0
        monto_facturado = 0
        purchase_orders = []
    
    # =========================================================================
    # 7. TOP PRODUCTOS RECEPCIONADOS
    # =========================================================================
    print("\n7️⃣  TOP 15 PRODUCTOS RECEPCIONADOS (MP con tipo/manejo)")
    print("-" * 80)
    
    productos_recepcionados = {}
    
    for mov in movimientos_mp:
        prod_id = mov.get('product_id', [None])[0]
        if prod_id in productos_map:
            if prod_id not in productos_recepcionados:
                productos_recepcionados[prod_id] = {
                    'nombre': productos_map[prod_id]['nombre'],
                    'tipo': productos_map[prod_id]['tipo'],
                    'manejo': productos_map[prod_id]['manejo'],
                    'kg_recepcionado': 0,
                    'kg_facturado': 0
                }
            productos_recepcionados[prod_id]['kg_recepcionado'] += mov.get('product_uom_qty', 0)
    
    # Agregar datos de facturación
    for prod_id, data in productos_facturados.items():
        if prod_id in productos_recepcionados:
            productos_recepcionados[prod_id]['kg_facturado'] = data['kg']
    
    # Ordenar por kg recepcionado
    top_productos = sorted(productos_recepcionados.items(), key=lambda x: x[1]['kg_recepcionado'], reverse=True)[:15]
    
    for i, (prod_id, data) in enumerate(top_productos, 1):
        diferencia = data['kg_recepcionado'] - data['kg_facturado']
        pct_facturado = (data['kg_facturado'] / data['kg_recepcionado'] * 100) if data['kg_recepcionado'] > 0 else 0
        
        print(f"{i:2d}. {data['nombre'][:45]}")
        print(f"    Tipo: {data['tipo']:<15} | Manejo: {data['manejo']}")
        print(f"    Recepcionado: {data['kg_recepcionado']:>10,.2f} kg")
        print(f"    Facturado:    {data['kg_facturado']:>10,.2f} kg ({pct_facturado:.1f}%)")
        print(f"    Diferencia:   {diferencia:>10,.2f} kg")
        print()
    
    # =========================================================================
    # RESUMEN FINAL
    # =========================================================================
    print("\n" + "="*80)
    print("RESUMEN CADENA COMPLETA")
    print("="*80)
    print(f"\n📦 RECEPCIONES:")
    print(f"   Total recepciones: {len(recepciones)}")
    print(f"   Total movimientos: {len(movimientos)}")
    print(f"   Total kg (todos): {total_kg_movimientos:,.2f}")
    
    print(f"\n🍓 MP CON TIPO/MANEJO:")
    print(f"   Productos: {con_tipo_manejo}")
    print(f"   Kg recepcionados: {kg_mp_recepcionado:,.2f}")
    
    print(f"\n📋 ÓRDENES DE COMPRA:")
    print(f"   Purchase orders: {len(purchase_orders) if purchase_orders else 0}")
    if purchase_orders:
        print(f"   Monto total: ${total_monto_po:,.2f}")
    
    print(f"\n📄 FACTURAS:")
    print(f"   Kg facturados: {kg_facturado:,.2f}")
    print(f"   Monto facturado: ${monto_facturado:,.2f}")
    
    print(f"\n⚖️  COMPARACIÓN:")
    print(f"   Kg recepcionados: {kg_mp_recepcionado:,.2f}")
    print(f"   Kg facturados:    {kg_facturado:,.2f}")
    print(f"   Diferencia:       {kg_mp_recepcionado - kg_facturado:,.2f} kg")
    print(f"   % Facturado:      {kg_facturado/kg_mp_recepcionado*100:.1f}%")
    
    print("="*80)
    
    print("\n💡 CONCLUSIÓN:")
    if kg_facturado < kg_mp_recepcionado * 0.5:
        print(f"   ⚠️  Solo se ha facturado {kg_facturado/kg_mp_recepcionado*100:.0f}% de lo recepcionado")
        print(f"   Faltan facturas por {kg_mp_recepcionado - kg_facturado:,.0f} kg")
        print(f"   Posibles causas:")
        print(f"   - Facturas emitidas fuera del período de análisis")
        print(f"   - Órdenes de compra pendientes de facturar")
        print(f"   - Recepciones sin orden de compra vinculada")

if __name__ == "__main__":
    trace_recepciones_a_facturas()
