#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis completo de OC11401: Línea con precio $6.5 que debe ser $1.6
"""
import xmlrpc.client

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

print("=" * 100)
print("ANÁLISIS COMPLETO: OC11401 - LÍNEA CON PRECIO INCORRECTO $6.5")
print("=" * 100)

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"\n✅ Conectado\n")

# ============================================================================
# PASO 1: DATOS DE LA OC
# ============================================================================
print("=" * 100)
print("PASO 1: DATOS DE OC11401")
print("=" * 100)

oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC11401']]],
    {'fields': [
        'id', 'name', 'partner_id', 'state', 'amount_total',
        'date_order', 'date_approve', 'invoice_status', 'invoice_ids',
        'picking_ids', 'order_line'
    ], 'limit': 1}
)

if not oc:
    print("❌ OC11401 no encontrada")
    exit(1)

oc = oc[0]
oc_id = oc['id']

print(f"\n📋 OC: {oc['name']} (ID: {oc_id})")
print(f"   Proveedor: {oc['partner_id'][1] if oc['partner_id'] else 'N/A'}")
print(f"   Estado: {oc['state']}")
print(f"   Estado Facturación: {oc.get('invoice_status', 'N/A')}")
print(f"   Total: ${oc['amount_total']:,.2f}")

# ============================================================================
# PASO 2: LÍNEAS DE LA OC - IDENTIFICAR CUÁL ESTÁ MAL
# ============================================================================
print("\n" + "=" * 100)
print("PASO 2: LÍNEAS DE LA ORDEN DE COMPRA")
print("=" * 100)

lineas_oc = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
    [[['order_id', '=', oc_id]]],
    {'fields': [
        'id', 'product_id', 'name', 'product_qty', 'price_unit',
        'price_subtotal', 'price_total', 'qty_received', 'qty_invoiced'
    ]}
)

print(f"\n📦 ENCONTRADAS {len(lineas_oc)} LÍNEAS:\n")

linea_incorrecta = None
for i, linea in enumerate(lineas_oc, 1):
    precio = linea['price_unit']
    print(f"Línea #{i} (ID: {linea['id']}):")
    print(f"  Producto: {linea['product_id'][1] if linea['product_id'] else 'N/A'}")
    print(f"  Cantidad: {linea['product_qty']} kg")
    print(f"  Precio Unit: ${precio:,.2f} {'⚠️ INCORRECTO' if precio == 6.5 else '✓'}")
    print(f"  Subtotal: ${linea['price_subtotal']:,.2f}")
    print(f"  Total: ${linea['price_total']:,.2f}")
    print(f"  Cantidad Recibida: {linea['qty_received']}")
    print(f"  Cantidad Facturada: {linea['qty_invoiced']}")
    
    if precio == 6.5:
        linea_incorrecta = linea
        print(f"  🎯 ESTA ES LA LÍNEA A CORREGIR → Debe ser $1.60")
    print()

if not linea_incorrecta:
    print("⚠️ No se encontró línea con precio $6.50")
    exit(1)

# ============================================================================
# PASO 3: RECEPCIONES - VERIFICAR SI HAY MOVIMIENTOS
# ============================================================================
print("\n" + "=" * 100)
print("PASO 3: RECEPCIONES / MOVIMIENTOS DE STOCK")
print("=" * 100)

picking_ids = oc.get('picking_ids', [])
if picking_ids:
    pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read',
        [[['id', 'in', picking_ids]]],
        {'fields': ['id', 'name', 'state', 'move_ids', 'date_done']}
    )
    
    print(f"\n📥 ENCONTRADOS {len(pickings)} ALBARANES:\n")
    
    moves_linea_incorrecta = []
    for picking in pickings:
        print(f"Albarán: {picking['name']} (Estado: {picking['state']}, Fecha: {picking.get('date_done', 'N/A')})")
        
        if picking.get('move_ids'):
            moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
                [[['id', 'in', picking['move_ids']]]],
                {'fields': [
                    'id', 'product_id', 'product_uom_qty', 'quantity_done',
                    'price_unit', 'state', 'purchase_line_id'
                ]}
            )
            
            for move in moves:
                pol_id = move.get('purchase_line_id')
                if pol_id:
                    pol_id = pol_id[0] if isinstance(pol_id, list) else pol_id
                    
                if pol_id == linea_incorrecta['id']:
                    print(f"  ✓ Movimiento ID {move['id']}: {move['product_id'][1] if move['product_id'] else 'N/A'}")
                    print(f"    Cantidad: {move['quantity_done']} kg")
                    print(f"    Precio Unit: ${move.get('price_unit', 0):,.2f} ⚠️")
                    print(f"    Estado: {move['state']}")
                    moves_linea_incorrecta.append(move)
        print()
else:
    print("\n⚠️ No hay recepciones")
    moves_linea_incorrecta = []

# ============================================================================
# PASO 4: CAPAS DE VALORACIÓN
# ============================================================================
print("\n" + "=" * 100)
print("PASO 4: CAPAS DE VALORACIÓN DE INVENTARIO")
print("=" * 100)

product_id = linea_incorrecta['product_id'][0] if linea_incorrecta.get('product_id') else None

if product_id and picking_ids:
    # Buscar por producto y precio 6.5
    valuation_layers = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'search_read',
        [[
            ['product_id', '=', product_id],
            ['unit_cost', '=', 6.5]
        ]],
        {'fields': [
            'id', 'product_id', 'quantity', 'unit_cost', 'value',
            'remaining_qty', 'remaining_value', 'description', 'create_date'
        ], 'limit': 10}
    )
    
    if valuation_layers:
        print(f"\n📉 ENCONTRADAS {len(valuation_layers)} CAPAS CON COSTO $6.50:\n")
        for vl in valuation_layers:
            print(f"Capa ID: {vl['id']}")
            print(f"  Producto: {vl['product_id'][1] if vl['product_id'] else 'N/A'}")
            print(f"  Fecha: {vl['create_date']}")
            print(f"  Descripción: {vl.get('description', 'N/A')}")
            print(f"  Cantidad: {vl['quantity']} kg")
            print(f"  Costo Unit: ${vl['unit_cost']:,.2f} ⚠️")
            print(f"  Valor: ${vl['value']:,.2f}")
            print(f"  Remaining Qty: {vl.get('remaining_qty', 0)}")
            print(f"  Remaining Value: ${vl.get('remaining_value', 0):,.2f}")
            print()
    else:
        print("\n⚠️ No se encontraron capas con costo $6.50")
else:
    print("\n⚠️ No se puede buscar valoración sin producto o sin recepciones")

# ============================================================================
# PASO 5: FACTURAS - VERIFICAR SI LA LÍNEA INCORRECTA ESTÁ FACTURADA
# ============================================================================
print("\n" + "=" * 100)
print("PASO 5: FACTURAS - VERIFICAR SI LA LÍNEA INCORRECTA ESTÁ FACTURADA")
print("=" * 100)

invoice_ids = oc.get('invoice_ids', [])
if invoice_ids:
    facturas = models.execute_kw(db, uid, password, 'account.move', 'search_read',
        [[['id', 'in', invoice_ids]]],
        {'fields': [
            'id', 'name', 'state', 'amount_total', 'invoice_line_ids'
        ]}
    )
    
    print(f"\n🧾 ENCONTRADAS {len(facturas)} FACTURAS:\n")
    
    linea_incorrecta_facturada = False
    for factura in facturas:
        print(f"Factura: {factura['name']} (Estado: {factura['state']}, Total: ${factura['amount_total']:,.2f})")
        
        if factura.get('invoice_line_ids'):
            lineas_fact = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
                [[['id', 'in', factura['invoice_line_ids']]]],
                {'fields': [
                    'id', 'product_id', 'quantity', 'price_unit',
                    'price_subtotal', 'purchase_line_id'
                ]}
            )
            
            for lf in lineas_fact:
                if lf.get('purchase_line_id'):
                    pol_id = lf['purchase_line_id'][0] if isinstance(lf['purchase_line_id'], list) else lf['purchase_line_id']
                    
                    if pol_id == linea_incorrecta['id']:
                        linea_incorrecta_facturada = True
                        print(f"  ⚠️  LÍNEA INCORRECTA FACTURADA:")
                        print(f"      Producto: {lf['product_id'][1] if lf['product_id'] else 'N/A'}")
                        print(f"      Cantidad: {lf['quantity']}")
                        print(f"      Precio: ${lf['price_unit']:,.2f}")
                        print(f"      Subtotal: ${lf['price_subtotal']:,.2f}")
        print()
    
    if not linea_incorrecta_facturada:
        print("✅ PERFECTO: La línea incorrecta NO está facturada")
        print("   Se puede corregir limpiamente\n")
else:
    print("\n✅ No hay facturas asociadas")

# ============================================================================
# RESUMEN Y PLAN DE CORRECCIÓN
# ============================================================================
print("\n" + "=" * 100)
print("RESUMEN Y PLAN DE CORRECCIÓN")
print("=" * 100)

print(f"""
🎯 LÍNEA A CORREGIR:
   ID: {linea_incorrecta['id']}
   Producto: {linea_incorrecta['product_id'][1] if linea_incorrecta['product_id'] else 'N/A'}
   Cantidad: {linea_incorrecta['product_qty']} kg
   Precio Actual: ${linea_incorrecta['price_unit']:,.2f}
   Precio Correcto: $1.60
   
📦 MOVIMIENTOS DE STOCK:
   Encontrados: {len(moves_linea_incorrecta)}
   A corregir de $6.50 → $1.60
   
📉 CAPAS DE VALORACIÓN:
   Con precio $6.50: {len(valuation_layers) if 'valuation_layers' in locals() and valuation_layers else 0}
   A corregir de $6.50 → $1.60
   
🧾 FACTURAS:
   Total facturas: {len(facturas) if invoice_ids else 0}
   Línea incorrecta facturada: {'SÍ ⚠️' if 'linea_incorrecta_facturada' in locals() and linea_incorrecta_facturada else 'NO ✓'}
   
{'✅ PUEDE CORREGIRSE LIMPIAMENTE' if not ('linea_incorrecta_facturada' in locals() and linea_incorrecta_facturada) else '⚠️  REQUIERE AJUSTE DE FACTURA'}

PASOS PARA CORRECCIÓN:
1. Actualizar purchase.order.line ID {linea_incorrecta['id']}: price_unit → $1.60
2. Actualizar {len(moves_linea_incorrecta)} movimientos de stock: price_unit → $1.60
3. Actualizar capas de valoración: unit_cost y value
{'4. Ajustar o crear nota de crédito en factura' if 'linea_incorrecta_facturada' in locals() and linea_incorrecta_facturada else ''}
""")

print("=" * 100)
