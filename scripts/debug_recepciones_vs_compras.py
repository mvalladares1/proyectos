"""
Script para comparar recepciones vs facturas de compra
Objetivo: Entender por qué los kg recepcionados no coinciden con las compras
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.odoo_client import OdooClient

def debug_recepciones_vs_compras():
    """Compara recepciones con facturas de compra."""
    
    username = input("Usuario Odoo: ")
    password = input("API Key: ")
    
    odoo = OdooClient(username=username, password=password)
    
    print("\n" + "="*80)
    print("COMPARACIÓN RECEPCIONES VS FACTURAS DE COMPRA")
    print("="*80)
    
    # =========================================================================
    # TEMPORADA ACTUAL: Nov 2025 - Ene 2026
    # =========================================================================
    print("\n📅 TEMPORADA ACTUAL: 2025-11-01 → 2026-01-20")
    print("="*80)
    
    fecha_desde_1 = "2025-11-01"
    fecha_hasta_1 = "2026-01-20"
    
    # RECEPCIONES (stock.picking de tipo incoming)
    print("\n1️⃣  RECEPCIONES (stock.picking)")
    print("-" * 80)
    
    recepciones_1 = odoo.search_read(
        'stock.picking',
        [
            ['picking_type_id.code', '=', 'incoming'],
            ['state', '=', 'done'],
            ['scheduled_date', '>=', fecha_desde_1],
            ['scheduled_date', '<=', fecha_hasta_1]
        ],
        ['name', 'scheduled_date', 'origin', 'partner_id'],
        limit=10000
    )
    
    print(f"Total recepciones: {len(recepciones_1)}")
    
    # Obtener movimientos de stock de esas recepciones
    picking_ids_1 = [r['id'] for r in recepciones_1]
    
    if picking_ids_1:
        movimientos_1 = odoo.search_read(
            'stock.move',
            [
                ['picking_id', 'in', picking_ids_1],
                ['state', '=', 'done']
            ],
            ['product_id', 'product_uom_qty', 'picking_id', 'purchase_line_id'],
            limit=100000
        )
        
        print(f"Total movimientos: {len(movimientos_1)}")
        
        total_kg_recepciones = sum(m.get('product_uom_qty', 0) for m in movimientos_1)
        print(f"Total kg recepcionados: {total_kg_recepciones:,.2f}")
        
        # Ver cuántos tienen purchase_line_id (vinculados a orden de compra)
        con_purchase = [m for m in movimientos_1 if m.get('purchase_line_id')]
        print(f"Movimientos con purchase_line_id: {len(con_purchase)} ({len(con_purchase)/len(movimientos_1)*100:.1f}%)")
    else:
        movimientos_1 = []
        total_kg_recepciones = 0
    
    # FACTURAS DE COMPRA (account.move)
    print("\n2️⃣  FACTURAS DE COMPRA (account.move)")
    print("-" * 80)
    
    facturas_1 = odoo.search_read(
        'account.move',
        [
            ['move_type', '=', 'in_invoice'],
            ['state', '=', 'posted'],
            ['invoice_date', '>=', fecha_desde_1],
            ['invoice_date', '<=', fecha_hasta_1]
        ],
        ['name', 'invoice_date', 'amount_total', 'partner_id'],
        limit=10000
    )
    
    print(f"Total facturas: {len(facturas_1)}")
    total_monto_facturas = sum(f.get('amount_total', 0) for f in facturas_1)
    print(f"Monto total: ${total_monto_facturas:,.2f}")
    
    # Líneas de facturas con producto
    factura_ids_1 = [f['id'] for f in facturas_1]
    
    if factura_ids_1:
        lineas_1 = odoo.search_read(
            'account.move.line',
            [
                ['move_id', 'in', factura_ids_1],
                ['product_id', '!=', False],
                ['quantity', '>', 0],
                ['debit', '>', 0]
            ],
            ['product_id', 'quantity', 'debit', 'purchase_line_id'],
            limit=100000
        )
        
        print(f"Líneas con producto: {len(lineas_1)}")
        total_kg_facturas = sum(l.get('quantity', 0) for l in lineas_1)
        total_debit = sum(l.get('debit', 0) for l in lineas_1)
        print(f"Total kg facturados: {total_kg_facturas:,.2f}")
        print(f"Total monto (debit): ${total_debit:,.2f}")
        
        # Ver cuántos tienen purchase_line_id
        con_purchase_fact = [l for l in lineas_1 if l.get('purchase_line_id')]
        print(f"Líneas con purchase_line_id: {len(con_purchase_fact)} ({len(con_purchase_fact)/len(lineas_1)*100:.1f}%)")
    else:
        lineas_1 = []
        total_kg_facturas = 0
        total_debit = 0
    
    # PRODUCTOS CON TIPO Y MANEJO
    print("\n3️⃣  ANÁLISIS DE PRODUCTOS")
    print("-" * 80)
    
    if lineas_1:
        prod_ids_1 = list(set([l.get('product_id', [None])[0] for l in lineas_1 if l.get('product_id')]))
        
        productos_1 = odoo.search_read(
            'product.product',
            [['id', 'in', prod_ids_1]],
            ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
            limit=10000
        )
        
        con_ambos = 0
        kg_con_ambos = 0
        monto_con_ambos = 0
        
        productos_map = {}
        for prod in productos_1:
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
            
            tiene_ambos = bool(tipo_str and manejo_str)
            if tiene_ambos:
                con_ambos += 1
            
            productos_map[prod['id']] = tiene_ambos
        
        for linea in lineas_1:
            prod_id = linea.get('product_id', [None])[0]
            if prod_id in productos_map and productos_map[prod_id]:
                kg_con_ambos += linea.get('quantity', 0)
                monto_con_ambos += linea.get('debit', 0)
        
        print(f"Productos únicos: {len(productos_1)}")
        print(f"Productos con tipo Y manejo: {con_ambos} ({con_ambos/len(productos_1)*100:.1f}%)")
        print(f"Kg con tipo y manejo: {kg_con_ambos:,.2f}")
        print(f"Monto con tipo y manejo: ${monto_con_ambos:,.2f}")
    
    print("\n" + "="*80)
    print("COMPARACIÓN TEMPORADA ACTUAL")
    print("="*80)
    print(f"Kg RECEPCIONADOS: {total_kg_recepciones:,.2f}")
    print(f"Kg FACTURADOS (total): {total_kg_facturas:,.2f}")
    print(f"Kg FACTURADOS (con tipo+manejo): {kg_con_ambos:,.2f}")
    print(f"")
    print(f"DIFERENCIA Recepciones vs Facturas: {total_kg_recepciones - total_kg_facturas:,.2f} kg")
    print(f"DIFERENCIA Recepciones vs Con tipo+manejo: {total_kg_recepciones - kg_con_ambos:,.2f} kg")
    
    # =========================================================================
    # ANALIZAR RECEPCIONES QUE NO TIENEN FACTURA
    # =========================================================================
    print("\n\n4️⃣  RECEPCIONES SIN FACTURA")
    print("="*80)
    
    # Obtener órdenes de compra vinculadas a recepciones
    if movimientos_1:
        purchase_line_ids = [m.get('purchase_line_id', [None])[0] for m in movimientos_1 if m.get('purchase_line_id')]
        purchase_line_ids = list(set([x for x in purchase_line_ids if x]))
        
        print(f"Purchase lines únicas en recepciones: {len(purchase_line_ids)}")
        
        if purchase_line_ids:
            # Obtener las órdenes de compra
            po_lines = odoo.search_read(
                'purchase.order.line',
                [['id', 'in', purchase_line_ids]],
                ['order_id', 'product_id', 'product_qty'],
                limit=10000
            )
            
            po_ids = list(set([l.get('order_id', [None])[0] for l in po_lines if l.get('order_id')]))
            print(f"Purchase orders únicas: {len(po_ids)}")
            
            if po_ids:
                purchase_orders = odoo.search_read(
                    'purchase.order',
                    [['id', 'in', po_ids]],
                    ['name', 'partner_id', 'invoice_status', 'state'],
                    limit=10000
                )
                
                # Contar por estado de facturación
                estados_facturacion = {}
                for po in purchase_orders:
                    estado = po.get('invoice_status', 'N/A')
                    estados_facturacion[estado] = estados_facturacion.get(estado, 0) + 1
                
                print("\nEstado de facturación de órdenes de compra:")
                for estado, count in estados_facturacion.items():
                    print(f"  {estado}: {count} órdenes")
    
    # =========================================================================
    # TEMPORADA PASADA: Nov 2024 - Ene 2025
    # =========================================================================
    print("\n\n" + "="*80)
    print("📅 TEMPORADA PASADA: 2024-11-01 → 2025-01-31")
    print("="*80)
    
    fecha_desde_2 = "2024-11-01"
    fecha_hasta_2 = "2025-01-31"
    
    # RECEPCIONES
    recepciones_2 = odoo.search_read(
        'stock.picking',
        [
            ['picking_type_id.code', '=', 'incoming'],
            ['state', '=', 'done'],
            ['scheduled_date', '>=', fecha_desde_2],
            ['scheduled_date', '<=', fecha_hasta_2]
        ],
        ['name', 'scheduled_date'],
        limit=10000
    )
    
    print(f"\nRecepciones: {len(recepciones_2)}")
    
    picking_ids_2 = [r['id'] for r in recepciones_2]
    
    if picking_ids_2:
        movimientos_2 = odoo.search_read(
            'stock.move',
            [
                ['picking_id', 'in', picking_ids_2],
                ['state', '=', 'done']
            ],
            ['product_id', 'product_uom_qty'],
            limit=100000
        )
        
        total_kg_recepciones_2 = sum(m.get('product_uom_qty', 0) for m in movimientos_2)
        print(f"Kg recepcionados: {total_kg_recepciones_2:,.2f}")
    else:
        total_kg_recepciones_2 = 0
    
    # FACTURAS
    facturas_2 = odoo.search_read(
        'account.move',
        [
            ['move_type', '=', 'in_invoice'],
            ['state', '=', 'posted'],
            ['invoice_date', '>=', fecha_desde_2],
            ['invoice_date', '<=', fecha_hasta_2]
        ],
        ['name', 'invoice_date', 'amount_total'],
        limit=10000
    )
    
    print(f"Facturas: {len(facturas_2)}")
    
    factura_ids_2 = [f['id'] for f in facturas_2]
    
    if factura_ids_2:
        lineas_2 = odoo.search_read(
            'account.move.line',
            [
                ['move_id', 'in', factura_ids_2],
                ['product_id', '!=', False],
                ['quantity', '>', 0],
                ['debit', '>', 0]
            ],
            ['product_id', 'quantity', 'debit'],
            limit=100000
        )
        
        total_kg_facturas_2 = sum(l.get('quantity', 0) for l in lineas_2)
        print(f"Kg facturados: {total_kg_facturas_2:,.2f}")
        
        # Productos con tipo y manejo
        prod_ids_2 = list(set([l.get('product_id', [None])[0] for l in lineas_2 if l.get('product_id')]))
        
        productos_2 = odoo.search_read(
            'product.product',
            [['id', 'in', prod_ids_2]],
            ['id', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
            limit=10000
        )
        
        productos_map_2 = {}
        for prod in productos_2:
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
            
            productos_map_2[prod['id']] = bool(tipo_str and manejo_str)
        
        kg_con_ambos_2 = 0
        for linea in lineas_2:
            prod_id = linea.get('product_id', [None])[0]
            if prod_id in productos_map_2 and productos_map_2[prod_id]:
                kg_con_ambos_2 += linea.get('quantity', 0)
        
        print(f"Kg con tipo y manejo: {kg_con_ambos_2:,.2f}")
    else:
        total_kg_facturas_2 = 0
        kg_con_ambos_2 = 0
    
    print("\n" + "="*80)
    print("COMPARACIÓN TEMPORADA PASADA")
    print("="*80)
    print(f"Kg RECEPCIONADOS: {total_kg_recepciones_2:,.2f}")
    print(f"Kg FACTURADOS (total): {total_kg_facturas_2:,.2f}")
    print(f"Kg FACTURADOS (con tipo+manejo): {kg_con_ambos_2:,.2f}")
    print(f"")
    print(f"DIFERENCIA Recepciones vs Facturas: {total_kg_recepciones_2 - total_kg_facturas_2:,.2f} kg")
    
    # =========================================================================
    # RESUMEN FINAL
    # =========================================================================
    print("\n\n" + "="*80)
    print("RESUMEN COMPARATIVO")
    print("="*80)
    print(f"\nTEMPORADA ACTUAL (Nov 2025 - Ene 2026):")
    print(f"  Recepciones: {total_kg_recepciones:,.2f} kg")
    print(f"  Facturas con tipo+manejo: {kg_con_ambos:,.2f} kg ({kg_con_ambos/total_kg_recepciones*100:.1f}%)")
    
    print(f"\nTEMPORADA PASADA (Nov 2024 - Ene 2025):")
    print(f"  Recepciones: {total_kg_recepciones_2:,.2f} kg")
    print(f"  Facturas con tipo+manejo: {kg_con_ambos_2:,.2f} kg ({kg_con_ambos_2/total_kg_recepciones_2*100:.1f}%)")
    
    print(f"\nTOTAL AMBAS TEMPORADAS:")
    print(f"  Recepciones: {total_kg_recepciones + total_kg_recepciones_2:,.2f} kg")
    print(f"  Facturas con tipo+manejo: {kg_con_ambos + kg_con_ambos_2:,.2f} kg")
    print("="*80)

if __name__ == "__main__":
    debug_recepciones_vs_compras()
