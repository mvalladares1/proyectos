#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis completo de OC11401: Impacto contable y operacional por error en precio
Precio incorrecto: $6.50 → Precio correcto: $1.60
"""
import xmlrpc.client
from datetime import datetime

# Conexión a Odoo
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

print("=" * 100)
print("ANÁLISIS COMPLETO: OC11401 - IMPACTO POR ERROR EN PRECIO")
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
# PASO 1: OBTENER DATOS COMPLETOS DE LA OC11401
# ============================================================================
print("\n" + "=" * 100)
print("PASO 1: DATOS DE LA ORDEN DE COMPRA OC11401")
print("=" * 100)

oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC11401']]],
    {'fields': [
        'id', 'name', 'partner_id', 'date_order', 'date_approve', 
        'amount_untaxed', 'amount_tax', 'amount_total', 'currency_id',
        'state', 'invoice_status', 'invoice_ids', 'picking_ids', 'order_line'
    ], 'limit': 1}
)

if not oc:
    print("❌ OC11401 no encontrada")
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
        'qty_invoiced', 'analytic_distribution'
    ]}
)

print(f"\n📦 ENCONTRADAS {len(lineas_oc)} LÍNEAS:\n")
total_calculado = 0
linea_correcta = None
linea_incorrecta = None

for i, linea in enumerate(lineas_oc, 1):
    print(f"Línea #{i}:")
    print(f"  ID: {linea['id']}")
    print(f"  Producto: {linea['product_id'][1] if linea['product_id'] else 'N/A'}")
    print(f"  Cantidad Pedida: {linea['product_qty']} {linea['product_uom'][1] if linea['product_uom'] else ''}")
    print(f"  Precio Unitario: ${linea['price_unit']:,.2f}")
    print(f"  Subtotal: ${linea['price_subtotal']:,.2f}")
    print(f"  Total (con IVA): ${linea['price_total']:,.2f}")
    print(f"  Cantidad Recibida: {linea['qty_received']}")
    print(f"  Cantidad Facturada: {linea['qty_invoiced']}")
    
    # Identificar líneas
    if linea['price_unit'] == 1.6:
        print(f"  ✓ PRECIO CORRECTO")
        linea_correcta = linea
    elif linea['price_unit'] == 6.5:
        print(f"  ⚠️  PRECIO INCORRECTO (debería ser $1.60)")
        linea_incorrecta = linea
    
    print()
    total_calculado += linea['price_total']

print(f"💵 TOTAL CALCULADO DE LÍNEAS: ${total_calculado:,.2f}")

if linea_correcta and linea_incorrecta:
    print(f"\n✓ CONFIRMADO: Hay una línea con precio correcto ($1.60) y otra con precio incorrecto ($6.50)")
    print(f"  Línea correcta (ID {linea_correcta['id']}): ${linea_correcta['price_unit']}")
    print(f"  Línea incorrecta (ID {linea_incorrecta['id']}): ${linea_incorrecta['price_unit']}")
    diferencia_precio = linea_incorrecta['price_unit'] - linea_correcta['price_unit']
    print(f"  Diferencia: ${diferencia_precio:,.2f}/unidad")

# ============================================================================
# PASO 3: RECEPCIONES / ALBARANES
# ============================================================================
print("\n" + "=" * 100)
print("PASO 3: RECEPCIONES / ALBARANES (MOVIMIENTOS DE INVENTARIO)")
print("=" * 100)

picking_ids = oc.get('picking_ids', [])
if picking_ids:
    pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read',
        [[['id', 'in', picking_ids]]],
        {'fields': ['id', 'name', 'state', 'scheduled_date', 'date_done', 'move_ids']}
    )
    
    print(f"\n📥 ENCONTRADAS {len(pickings)} RECEPCIONES:\n")
    
    for picking in pickings:
        print(f"Recepción: {picking['name']}")
        print(f"  Estado: {picking['state']}")
        print(f"  Fecha Programada: {picking['scheduled_date']}")
        print(f"  Fecha Realizada: {picking.get('date_done', 'N/A')}")
        
        if picking.get('move_ids'):
            moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
                [[['id', 'in', picking['move_ids']]]],
                {'fields': ['product_id', 'product_uom_qty', 'quantity_done', 'price_unit', 'state']}
            )
            print(f"  Movimientos de Stock: {len(moves)}")
            for move in moves:
                print(f"    - {move['product_id'][1] if move['product_id'] else 'N/A'}")
                print(f"      Cantidad: {move['quantity_done']} (demanda: {move['product_uom_qty']})")
                print(f"      Precio Unit: ${move.get('price_unit', 0):,.2f}")
                print(f"      Estado: {move['state']}")
        print()
else:
    print("\n⚠️ No hay recepciones asociadas a esta OC")

# ============================================================================
# PASO 4: FACTURAS
# ============================================================================
print("\n" + "=" * 100)
print("PASO 4: FACTURAS DE PROVEEDOR RELACIONADAS")
print("=" * 100)

invoice_ids = oc.get('invoice_ids', [])
if invoice_ids:
    facturas = models.execute_kw(db, uid, password, 'account.move', 'search_read',
        [[['id', 'in', invoice_ids]]],
        {'fields': ['id', 'name', 'state', 'invoice_date', 'amount_total', 'invoice_line_ids']}
    )
    
    print(f"\n🧾 ENCONTRADAS {len(facturas)} FACTURAS:\n")
    
    for factura in facturas:
        print(f"Factura: {factura['name']}")
        print(f"  ID: {factura['id']}")
        print(f"  Estado: {factura['state']} {'✓ (borrador)' if factura['state'] == 'draft' else '⚠️ (contabilizada)'}")
        print(f"  Fecha: {factura.get('invoice_date', 'N/A')}")
        print(f"  Total: ${factura['amount_total']:,.2f}")
        print()
else:
    print("\n⚠️ No hay facturas asociadas a esta OC todavía")

# ============================================================================
# PASO 5: CAPAS DE VALORACIÓN
# ============================================================================
print("\n" + "=" * 100)
print("PASO 5: CAPAS DE VALORACIÓN DE INVENTARIO")
print("=" * 100)

if lineas_oc:
    product_ids = [l['product_id'][0] for l in lineas_oc if l.get('product_id')]
    
    # Buscar por fecha de la OC
    fecha_oc = oc['date_order'][:10]  # YYYY-MM-DD
    
    valuation_layers = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'search_read',
        [[
            ['product_id', 'in', product_ids],
            ['create_date', '>=', fecha_oc],
            ['create_date', '<=', fecha_oc + ' 23:59:59']
        ]],
        {'fields': ['id', 'product_id', 'quantity', 'unit_cost', 'value', 'description']}
    )
    
    if valuation_layers:
        print(f"\n📉 ENCONTRADAS {len(valuation_layers)} CAPAS DE VALORACIÓN:\n")
        for vl in valuation_layers:
            print(f"Capa ID: {vl['id']}")
            print(f"  Producto: {vl['product_id'][1] if vl['product_id'] else 'N/A'}")
            print(f"  Cantidad: {vl['quantity']}")
            print(f"  Costo Unitario: ${vl['unit_cost']:,.2f}")
            print(f"  Valor Total: ${vl['value']:,.2f}")
            print(f"  Descripción: {vl.get('description', 'N/A')}")
            
            # Marcar si es incorrecto
            if vl['unit_cost'] == 6.5:
                print(f"  ⚠️  COSTO INCORRECTO (debería ser $1.60)")
            
            print()
    else:
        print(f"\n⚠️ No hay capas de valoración para {fecha_oc}")

# ============================================================================
# RESUMEN
# ============================================================================
print("\n" + "=" * 100)
print("RESUMEN EJECUTIVO")
print("=" * 100)

print(f"""
📌 ORDEN DE COMPRA: {oc['name']}
   Proveedor: {oc['partner_id'][1] if oc['partner_id'] else 'N/A'}
   Total: ${oc['amount_total']:,.2f}
   Estado: {oc['state']}

🔍 ANÁLISIS DEL ERROR:
   {"✓ Detectada línea con precio incorrecto $6.50 (debería ser $1.60)" if linea_incorrecta else "❌ No se detectó error de precio"}
   {"✓ Existe línea de referencia con precio correcto $1.60" if linea_correcta else ""}

📦 IMPACTO OPERACIONAL:
   Recepciones: {len(pickings) if picking_ids else 0}
   
💰 IMPACTO CONTABLE:
   Facturas: {len(facturas) if invoice_ids else 0}
   
🎯 SIGUIENTE PASO:
   {"✓ Ejecutar DRY-RUN para simular corrección" if linea_incorrecta and not invoice_ids else ""}
   {"⚠️  REVISAR: Ya existen facturas, corrección más compleja" if invoice_ids else ""}
""")

print("=" * 100)
print("FIN DEL ANÁLISIS")
print("=" * 100)
