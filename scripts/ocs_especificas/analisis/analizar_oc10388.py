#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis de OC10388 con error de precio
Precio correcto: 2850.0
"""
import xmlrpc.client

# ============= CONFIGURACIÓN =============
OC_NAME = 'OC10388'
PRECIO_CORRECTO = 2850.0
CANTIDAD_CORRECTA = None

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

print("=" * 120)
print(f"ANÁLISIS COMPLETO: {OC_NAME}")
print("=" * 120)

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"\n✅ Conectado\n")

# ========== PASO 1: ORDEN DE COMPRA ==========
print("=" * 120)
print("PASO 1: INFORMACIÓN DE LA OC")
print("=" * 120)

oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', OC_NAME]]],
    {'fields': ['id', 'partner_id', 'date_order', 'state', 'currency_id', 'amount_total', 'invoice_status'], 'limit': 1}
)

if not oc:
    print(f"❌ {OC_NAME} no encontrada")
    exit(1)

oc = oc[0]
oc_id = oc['id']

print(f"\n📋 {OC_NAME} (ID: {oc_id})")
print(f"   Proveedor: {oc['partner_id'][1] if oc['partner_id'] else 'N/A'}")
print(f"   Fecha: {oc['date_order']}")
print(f"   Estado: {oc['state']}")
print(f"   Estado facturación: {oc['invoice_status']}")
print(f"   Moneda: {oc['currency_id'][1] if oc['currency_id'] else 'N/A'}")
print(f"   Total: ${oc['amount_total']:,.2f}")

# ========== PASO 2: LÍNEAS DE COMPRA ==========
print("\n" + "=" * 120)
print("PASO 2: LÍNEAS DE COMPRA")
print("=" * 120)

lineas = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
    [[['order_id', '=', oc_id]]],
    {'fields': ['id', 'product_id', 'product_qty', 'qty_received', 'qty_invoiced', 'price_unit', 'price_subtotal']}
)

print(f"\n📦 Total de líneas: {len(lineas)}\n")

for linea in lineas:
    print(f"Línea ID {linea['id']}:")
    print(f"  Producto: {linea['product_id'][1] if linea['product_id'] else 'N/A'}")
    print(f"  Cantidad pedida: {linea['product_qty']:,.3f}")
    print(f"  Cantidad recibida: {linea.get('qty_received', 0):,.3f}")
    print(f"  Cantidad facturada: {linea.get('qty_invoiced', 0):,.3f}")
    print(f"  Precio unitario: ${linea['price_unit']:,.2f}")
    print(f"  Subtotal: ${linea['price_subtotal']:,.2f}")
    
    if PRECIO_CORRECTO and abs(linea['price_unit'] - PRECIO_CORRECTO) >= 0.01:
        print(f"  ⚠️  ERROR PRECIO: ${linea['price_unit']:,.2f} → debe ser ${PRECIO_CORRECTO:,.2f}")
    
    if CANTIDAD_CORRECTA and abs(linea['product_qty'] - CANTIDAD_CORRECTA) >= 0.01:
        print(f"  ⚠️  ERROR CANTIDAD: {linea['product_qty']:,.3f} → debe ser {CANTIDAD_CORRECTA:,.3f}")
    print()

# ========== PASO 3: RECEPCIONES ==========
print("=" * 120)
print("PASO 3: RECEPCIONES")
print("=" * 120)

pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read',
    [[['origin', '=', OC_NAME]]],
    {'fields': ['id', 'name', 'state', 'date_done', 'picking_type_id']}
)

print(f"\n📦 Total de recepciones: {len(pickings)}\n")

for picking in pickings:
    print(f"Recepción: {picking['name']} (ID: {picking['id']})")
    print(f"  Estado: {picking['state']}")
    print(f"  Fecha: {picking.get('date_done', 'N/A')}")
    
    # Movimientos de esta recepción
    moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
        [[['picking_id', '=', picking['id']]]],
        {'fields': ['id', 'product_id', 'product_uom_qty', 'quantity_done', 'price_unit', 'state']}
    )
    
    for move in moves:
        print(f"  └─ Movimiento ID {move['id']}:")
        print(f"     Producto: {move['product_id'][1] if move['product_id'] else 'N/A'}")
        print(f"     Cantidad: Esperada {move['product_uom_qty']:,.3f}, Realizada {move['quantity_done']:,.3f}")
        print(f"     Precio unitario: ${move.get('price_unit', 0):,.2f}")
        print(f"     Estado: {move['state']}")
        
        if PRECIO_CORRECTO and move.get('price_unit', 0) != 0:
            if abs(move['price_unit'] - PRECIO_CORRECTO) >= 0.01:
                print(f"     ⚠️  ERROR PRECIO MOVIMIENTO: ${move['price_unit']:,.2f} → debe ser ${PRECIO_CORRECTO:,.2f}")
    print()

# ========== PASO 4: FACTURAS ==========
print("=" * 120)
print("PASO 4: FACTURAS")
print("=" * 120)

facturas = models.execute_kw(db, uid, password, 'account.move', 'search_read',
    [[['ref', 'ilike', OC_NAME], ['move_type', 'in', ['in_invoice', 'in_refund']]]],
    {'fields': ['id', 'name', 'ref', 'state', 'invoice_date', 'amount_total', 'currency_id'], 'limit': 10}
)

print(f"\n🧾 Total de facturas: {len(facturas)}\n")

for factura in facturas:
    print(f"Factura: {factura['name']} (ID: {factura['id']})")
    print(f"  Estado: {factura['state']}")
    print(f"  Fecha: {factura.get('invoice_date', 'N/A')}")
    print(f"  Monto: ${factura['amount_total']:,.2f} {factura['currency_id'][1] if factura['currency_id'] else ''}")
    
    if factura['state'] == 'draft':
        print(f"  ⚠️  FACTURA EN BORRADOR - Se debe eliminar antes de corregir")
    elif factura['state'] == 'posted':
        print(f"  ⛔ FACTURA CONFIRMADA - Requiere nota de crédito para corregir")
    print()

# ========== PASO 5: CAPAS DE VALORACIÓN ==========
print("=" * 120)
print("PASO 5: CAPAS DE VALORACIÓN DE INVENTARIO")
print("=" * 120)

# Buscar por stock_move_id si hay movimientos
if pickings:
    for picking in pickings:
        moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
            [[['picking_id', '=', picking['id']]]],
            {'fields': ['id']}
        )
        
        for move in moves:
            layers_by_move = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'search_read',
                [[['stock_move_id', '=', move['id']]]],
                {'fields': ['id', 'quantity', 'unit_cost', 'value', 'product_id']}
            )
            
            for layer in layers_by_move:
                print(f"Capa ID {layer['id']} (stock_move_id={move['id']}):")
                print(f"  Producto: {layer['product_id'][1] if layer['product_id'] else 'N/A'}")
                print(f"  Cantidad: {layer['quantity']:,.3f}")
                print(f"  Costo unitario: ${layer['unit_cost']:,.2f}")
                print(f"  Valor total: ${layer['value']:,.2f}")
                
                if PRECIO_CORRECTO and abs(layer['unit_cost'] - PRECIO_CORRECTO) >= 0.01:
                    print(f"  ⚠️  ERROR COSTO: ${layer['unit_cost']:,.2f} → debe ser ${PRECIO_CORRECTO:,.2f}")
                    print(f"  ⚠️  Valor correcto debería ser: ${layer['quantity'] * PRECIO_CORRECTO:,.2f}")
                print()

# ========== RESUMEN ==========
print("=" * 120)
print("RESUMEN Y RECOMENDACIONES")
print("=" * 120)

print(f"\n📋 {OC_NAME}")
print(f"\n✅ PREREQUISITOS:")
print(f"   Estado OC: {oc['state']}")
print(f"   Facturas borrador: {len([f for f in facturas if f['state'] == 'draft'])}")
print(f"   Facturas confirmadas: {len([f for f in facturas if f['state'] == 'posted'])}")

print(f"\n🔧 CORRECCIONES NECESARIAS:")
if PRECIO_CORRECTO:
    print(f"   Precio: → ${PRECIO_CORRECTO:,.2f}")
if CANTIDAD_CORRECTA:
    print(f"   Cantidad: → {CANTIDAD_CORRECTA:,.3f}")

print(f"\n📝 ACCIONES RECOMENDADAS:")
print(f"   1. {'❌ Eliminar facturas borrador' if any(f['state'] == 'draft' for f in facturas) else '✓ No hay facturas borrador'}")
print(f"   2. {'⛔ NO CONTINUAR - requiere nota de crédito' if any(f['state'] == 'posted' for f in facturas) else '✓ Sin facturas confirmadas, puede corregir'}")
print(f"   3. Actualizar purchase.order.line")
print(f"   4. Actualizar stock.move (corrección en cadena)")
print(f"   5. Actualizar stock.valuation.layer (corrección en cadena)")

print("\n" + "=" * 120)
print("FIN DEL ANÁLISIS")
print("=" * 120)
