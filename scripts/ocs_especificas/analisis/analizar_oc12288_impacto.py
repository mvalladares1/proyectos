#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis completo de OC12288: Impacto contable y operacional por error en precio
"""
import xmlrpc.client
from datetime import datetime
from collections import defaultdict
import json

# Conexión a Odoo
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

print("=" * 100)
print("ANÁLISIS COMPLETO: OC12288 - IMPACTO POR ERROR EN PRECIO")
print("=" * 100)

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

if not uid:
    print("❌ Error de autenticación")
    exit(1)

print(f"\n✅ Conectado como UID: {uid}\n")

# ============================================================================
# PASO 1: OBTENER DATOS COMPLETOS DE LA OC12288
# ============================================================================
print("\n" + "=" * 100)
print("PASO 1: DATOS DE LA ORDEN DE COMPRA OC12288")
print("=" * 100)

oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC12288']]],
    {'fields': [
        'id', 'name', 'partner_id', 'date_order', 'date_approve', 
        'amount_untaxed', 'amount_tax', 'amount_total', 'currency_id',
        'state', 'invoice_status', 'invoice_ids', 'picking_ids',
        'order_line', 'payment_term_id', 'notes', 'user_id'
    ], 'limit': 1}
)

if not oc:
    print("❌ OC12288 no encontrada")
    exit(1)

oc = oc[0]
oc_id = oc['id']

print(f"\n📋 INFORMACIÓN GENERAL:")
print(f"  ID: {oc_id}")
print(f"  Nombre: {oc['name']}")
print(f"  Proveedor: {oc['partner_id'][1] if oc['partner_id'] else 'N/A'}")
print(f"  Fecha Orden: {oc['date_order']}")
print(f"  Fecha Aprobación: {oc['date_approve']}")
print(f"  Estado: {oc['state']}")
print(f"  Estado Facturación: {oc['invoice_status']}")
print(f"\n💰 IMPORTES:")
print(f"  Subtotal: ${oc['amount_untaxed']:,.2f}")
print(f"  Impuestos: ${oc['amount_tax']:,.2f}")
print(f"  TOTAL: ${oc['amount_total']:,.2f}")
print(f"  Moneda: {oc['currency_id'][1] if oc['currency_id'] else 'N/A'}")

# ============================================================================
# PASO 2: LÍNEAS DE LA ORDEN DE COMPRA
# ============================================================================
print("\n" + "=" * 100)
print("PASO 2: LÍNEAS DE LA ORDEN DE COMPRA (DETALLES DE PRODUCTOS Y PRECIOS)")
print("=" * 100)

lineas_oc = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
    [[['order_id', '=', oc_id]]],
    {'fields': [
        'id', 'product_id', 'name', 'product_qty', 'product_uom', 
        'price_unit', 'price_subtotal', 'price_total', 'qty_received',
        'qty_invoiced', 'analytic_distribution', 'taxes_id'
    ]}
)

print(f"\n📦 ENCONTRADAS {len(lineas_oc)} LÍNEAS:\n")
total_calculado = 0
for i, linea in enumerate(lineas_oc, 1):
    print(f"Línea #{i}:")
    print(f"  Producto: {linea['product_id'][1] if linea['product_id'] else 'N/A'}")
    print(f"  Descripción: {linea['name'][:80]}")
    print(f"  Cantidad Pedida: {linea['product_qty']} {linea['product_uom'][1] if linea['product_uom'] else ''}")
    print(f"  Precio Unitario: ${linea['price_unit']:,.2f} ⚠️")
    print(f"  Subtotal: ${linea['price_subtotal']:,.2f}")
    print(f"  Total (con IVA): ${linea['price_total']:,.2f}")
    print(f"  Cantidad Recibida: {linea['qty_received']}")
    print(f"  Cantidad Facturada: {linea['qty_invoiced']}")
    if linea.get('analytic_distribution'):
        print(f"  Distribución Analítica: {linea['analytic_distribution']}")
    print()
    total_calculado += linea['price_total']

print(f"💵 TOTAL CALCULADO DE LÍNEAS: ${total_calculado:,.2f}")

# ============================================================================
# PASO 3: RECEPCIONES / ALBARANES (STOCK.PICKING)
# ============================================================================
print("\n" + "=" * 100)
print("PASO 3: RECEPCIONES / ALBARANES (MOVIMIENTOS DE INVENTARIO)")
print("=" * 100)

picking_ids = oc.get('picking_ids', [])
if picking_ids:
    pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read',
        [[['id', 'in', picking_ids]]],
        {'fields': [
            'id', 'name', 'state', 'picking_type_id', 'location_id',
            'location_dest_id', 'scheduled_date', 'date_done', 'move_ids'
        ]}
    )
    
    print(f"\n📥 ENCONTRADAS {len(pickings)} RECEPCIONES:\n")
    
    for picking in pickings:
        print(f"Recepción: {picking['name']}")
        print(f"  Estado: {picking['state']}")
        print(f"  Tipo: {picking['picking_type_id'][1] if picking['picking_type_id'] else 'N/A'}")
        print(f"  Fecha Programada: {picking['scheduled_date']}")
        print(f"  Fecha Realizada: {picking.get('date_done', 'N/A')}")
        
        # Obtener movimientos de stock
        if picking.get('move_ids'):
            moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
                [[['id', 'in', picking['move_ids']]]],
                {'fields': [
                    'product_id', 'product_uom_qty', 'quantity_done', 'state',
                    'price_unit'
                ]}
            )
            print(f"  Movimientos de Stock: {len(moves)}")
            for move in moves:
                print(f"    - {move['product_id'][1] if move['product_id'] else 'N/A'}")
                print(f"      Cantidad demandada: {move['product_uom_qty']}, Realizada: {move['quantity_done']}")
                print(f"      Precio Unit: ${move.get('price_unit', 0):,.2f} ⚠️")
                print(f"      Estado: {move['state']}")
        print()
else:
    print("\n⚠️ No hay recepciones asociadas a esta OC")

# ============================================================================
# PASO 4: FACTURAS DE PROVEEDOR (ACCOUNT.MOVE)
# ============================================================================
print("\n" + "=" * 100)
print("PASO 4: FACTURAS DE PROVEEDOR RELACIONADAS")
print("=" * 100)

invoice_ids = oc.get('invoice_ids', [])
if invoice_ids:
    facturas = models.execute_kw(db, uid, password, 'account.move', 'search_read',
        [[['id', 'in', invoice_ids]]],
        {'fields': [
            'id', 'name', 'ref', 'invoice_date', 'date', 'state', 'move_type',
            'amount_untaxed', 'amount_tax', 'amount_total', 'amount_residual',
            'payment_state', 'invoice_line_ids', 'line_ids'
        ]}
    )
    
    print(f"\n🧾 ENCONTRADAS {len(facturas)} FACTURAS:\n")
    
    for factura in facturas:
        print(f"Factura: {factura['name']}")
        print(f"  Referencia: {factura.get('ref', 'N/A')}")
        print(f"  Fecha Factura: {factura.get('invoice_date', 'N/A')}")
        print(f"  Fecha Contable: {factura.get('date', 'N/A')}")
        print(f"  Estado: {factura['state']}")
        print(f"  Estado Pago: {factura.get('payment_state', 'N/A')}")
        print(f"  Subtotal: ${factura['amount_untaxed']:,.2f}")
        print(f"  Impuestos: ${factura['amount_tax']:,.2f}")
        print(f"  Total: ${factura['amount_total']:,.2f}")
        print(f"  Saldo Pendiente: ${factura.get('amount_residual', 0):,.2f}")
        
        # Obtener líneas de factura
        if factura.get('invoice_line_ids'):
            lineas_fact = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
                [[['id', 'in', factura['invoice_line_ids']]]],
                {'fields': [
                    'product_id', 'name', 'quantity', 'price_unit', 
                    'price_subtotal', 'price_total', 'account_id',
                    'analytic_distribution', 'purchase_line_id'
                ]}
            )
            print(f"\n  Líneas de Factura ({len(lineas_fact)}):")
            for lf in lineas_fact:
                print(f"    - {lf['product_id'][1] if lf['product_id'] else 'N/A'}")
                print(f"      Cantidad: {lf['quantity']}")
                print(f"      Precio Unit: ${lf['price_unit']:,.2f}")
                print(f"      Subtotal: ${lf['price_subtotal']:,.2f}")
                print(f"      Cuenta: {lf['account_id'][1] if lf['account_id'] else 'N/A'}")
        print()
else:
    print("\n⚠️ No hay facturas asociadas a esta OC todavía")

# ============================================================================
# PASO 5: ASIENTOS CONTABLES COMPLETOS
# ============================================================================
print("\n" + "=" * 100)
print("PASO 5: ASIENTOS CONTABLES RELACIONADOS")
print("=" * 100)

# Buscar todos los asientos contables que mencionen la OC12288
asientos = models.execute_kw(db, uid, password, 'account.move', 'search_read',
    [[
        '|', '|',
        ['ref', 'ilike', 'OC12288'],
        ['narration', 'ilike', 'OC12288'],
        ['id', 'in', invoice_ids if invoice_ids else [0]]
    ]],
    {'fields': [
        'id', 'name', 'date', 'ref', 'journal_id', 'state',
        'amount_total', 'line_ids'
    ]}
)

print(f"\n📊 ENCONTRADOS {len(asientos)} ASIENTOS CONTABLES:\n")

for asiento in asientos:
    print(f"Asiento: {asiento['name']}")
    print(f"  Fecha: {asiento['date']}")
    print(f"  Referencia: {asiento.get('ref', 'N/A')}")
    print(f"  Diario: {asiento['journal_id'][1] if asiento['journal_id'] else 'N/A'}")
    print(f"  Estado: {asiento['state']}")
    print(f"  Total: ${asiento.get('amount_total', 0):,.2f}")
    
    # Obtener líneas del asiento
    if asiento.get('line_ids'):
        lineas_asiento = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
            [[['id', 'in', asiento['line_ids']]]],
            {'fields': [
                'account_id', 'name', 'debit', 'credit', 'balance',
                'partner_id', 'analytic_distribution'
            ]}
        )
        print(f"\n  Detalle del Asiento ({len(lineas_asiento)} líneas):")
        print(f"  {'Cuenta':<50} {'Debe':>15} {'Haber':>15} {'Balance':>15}")
        print(f"  {'-'*50} {'-'*15} {'-'*15} {'-'*15}")
        
        total_debe = 0
        total_haber = 0
        for la in lineas_asiento:
            cuenta = la['account_id'][1] if la['account_id'] else 'N/A'
            debe = la.get('debit', 0)
            haber = la.get('credit', 0)
            balance = la.get('balance', 0)
            total_debe += debe
            total_haber += haber
            print(f"  {cuenta[:50]:<50} ${debe:>14,.2f} ${haber:>14,.2f} ${balance:>14,.2f}")
            
            if la.get('analytic_distribution'):
                print(f"    Analítica: {la['analytic_distribution']}")
        
        print(f"  {'-'*50} {'-'*15} {'-'*15} {'-'*15}")
        print(f"  {'TOTAL':<50} ${total_debe:>14,.2f} ${total_haber:>14,.2f}")
        print()

# ============================================================================
# PASO 6: PAGOS REALIZADOS
# ============================================================================
print("\n" + "=" * 100)
print("PASO 6: PAGOS REALIZADOS (SI APLICA)")
print("=" * 100)

# Buscar pagos relacionados con las facturas
if invoice_ids:
    # Buscar account.payment relacionados
    pagos = models.execute_kw(db, uid, password, 'account.payment', 'search_read',
        [[
            ['reconciled_invoice_ids', 'in', invoice_ids]
        ]],
        {'fields': [
            'id', 'name', 'date', 'amount', 'state', 'payment_type',
            'partner_id', 'journal_id', 'ref', 'reconciled_invoice_ids'
        ]}
    )
    
    if pagos:
        print(f"\n💳 ENCONTRADOS {len(pagos)} PAGOS:\n")
        for pago in pagos:
            print(f"Pago: {pago['name']}")
            print(f"  Fecha: {pago['date']}")
            print(f"  Monto: ${pago['amount']:,.2f}")
            print(f"  Estado: {pago['state']}")
            print(f"  Tipo: {pago['payment_type']}")
            print(f"  Partner: {pago['partner_id'][1] if pago['partner_id'] else 'N/A'}")
            print(f"  Diario: {pago['journal_id'][1] if pago['journal_id'] else 'N/A'}")
            print()
    else:
        print("\n⚠️ No hay pagos registrados para las facturas de esta OC")
else:
    print("\n⚠️ No hay facturas, por lo tanto no hay pagos")

# ============================================================================
# PASO 7: AJUSTES DE INVENTARIO RELACIONADOS
# ============================================================================
print("\n" + "=" * 100)
print("PASO 7: AJUSTES DE INVENTARIO O VALORACIONES")
print("=" * 100)

# Buscar en stock.valuation.layer relacionadas con el picking
try:
    if lineas_oc:
        product_ids = [l['product_id'][0] for l in lineas_oc if l.get('product_id')]
        
        valuation_layers = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'search_read',
            [[
                ['product_id', 'in', product_ids],
                ['create_date', '>=', '2026-01-28'],
                ['create_date', '<=', '2026-01-29']
            ]],
            {'fields': [
                'id', 'create_date', 'product_id', 'quantity', 'unit_cost',
                'value', 'remaining_qty', 'remaining_value', 'description',
                'stock_move_id'
            ]}
        )
        
        if valuation_layers:
            print(f"\n📉 ENCONTRADAS {len(valuation_layers)} CAPAS DE VALORACIÓN (filtradas por fecha y producto):\n")
            for vl in valuation_layers:
                print(f"Capa de Valoración ID: {vl['id']}")
                print(f"  Fecha: {vl['create_date']}")
                print(f"  Producto: {vl['product_id'][1] if vl['product_id'] else 'N/A'}")
                print(f"  Cantidad: {vl['quantity']}")
                print(f"  Costo Unitario: ${vl['unit_cost']:,.2f} ⚠️")
                print(f"  Valor Total: ${vl['value']:,.2f} ⚠️")
                print(f"  Cantidad Remanente: {vl.get('remaining_qty', 0)}")
                print(f"  Valor Remanente: ${vl.get('remaining_value', 0):,.2f}")
                if vl.get('description'):
                    print(f"  Descripción: {vl['description']}")
                print()
        else:
            print("\n⚠️ No hay capas de valoración registradas para estos productos en esta fecha")
    else:
        print("\n⚠️ No se pueden buscar valoraciones sin productos")
except Exception as e:
    print(f"\n⚠️ Error al buscar valoraciones: {e}")
    print("   (Esto puede deberse a permisos o estructura de datos)")

# ============================================================================
# RESUMEN EJECUTIVO
# ============================================================================
print("\n" + "=" * 100)
print("RESUMEN EJECUTIVO: IMPACTO DEL ERROR EN PRECIO")
print("=" * 100)

print(f"""
📌 ORDEN DE COMPRA: {oc['name']}

🔢 DATOS PRINCIPALES:
   - Proveedor: {oc['partner_id'][1] if oc['partner_id'] else 'N/A'}
   - Total OC: ${oc['amount_total']:,.2f}
   - Estado: {oc['state']}
   - Líneas de productos: {len(lineas_oc)}

📦 IMPACTO OPERACIONAL:
   - Recepciones generadas: {len(pickings) if picking_ids else 0}
   - Estado de entregas: {"Completadas" if picking_ids else "Pendientes"}

💰 IMPACTO CONTABLE:
   - Facturas generadas: {len(facturas) if invoice_ids else 0}
   - Asientos contables: {len(asientos)}
   - Pagos realizados: {len(pagos) if invoice_ids and 'pagos' in locals() else 0}

🎯 SIGUIENTE PASO:
   {"✓ Revisar los precios unitarios de las líneas mostradas arriba" if lineas_oc else ""}
   {"✓ Analizar si las facturas reflejan el precio incorrecto" if invoice_ids else ""}
   {"✓ Verificar ajustes de valoración de inventario" if picking_ids else ""}
   {"⚠️ PUEDE REQUERIR: Nota de crédito/débito para corregir el error en precio" if invoice_ids else ""}

""")

print("=" * 100)
print("FIN DEL ANÁLISIS")
print("=" * 100)
