#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RECUENTO COMPLETO: IMPACTO CONTABLE DE TODAS LAS OCs CORREGIDAS
Análisis de: OC12288, OC11401, OC12902, OC09581, OC12755, OC13491, OC13530, OC13596
"""
import xmlrpc.client
import json
from datetime import datetime

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

OCS_CORREGIDAS = [
    'OC12288',  # Precio $0→$2.0
    'OC11401',  # Precio $6.5→$1.6 + eliminación factura
    'OC12902',  # Precio 3080→3085 CLP
    'OC09581',  # Cantidad 103→746.65
    'OC12755',  # Precio $0→$2,000 + cantidad 110→138.480
    'OC13491',  # Precio $3,400→$3,300 + cantidad 5,015→4,975.760
    'OC13530',  # Precio $3,400→$3,300 + cantidad 4,730→4,566.060
    'OC13596'   # Precio $3,400→$3,300 + cantidad 3,125→3,104.160
]

print("=" * 120)
print(" " * 30 + "RECUENTO COMPLETO DE OCs CORREGIDAS")
print("=" * 120)
print(f"\n📋 Total de OCs analizadas: {len(OCS_CORREGIDAS)}\n")

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"✅ Conectado a Odoo\n")

resumen_general = {
    'fecha_analisis': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'ocs_analizadas': len(OCS_CORREGIDAS),
    'detalles': {}
}

total_impacto_monetario = 0

for idx, oc_name in enumerate(OCS_CORREGIDAS, 1):
    print("=" * 120)
    print(f"OC {idx}/{len(OCS_CORREGIDAS)}: {oc_name}")
    print("=" * 120)
    
    detalle_oc = {
        'nombre': oc_name,
        'estado': None,
        'impacto': {}
    }
    
    # ========== PASO 1: ORDEN DE COMPRA ==========
    oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
        [[['name', '=', oc_name]]],
        {'fields': ['id', 'partner_id', 'date_order', 'state', 'currency_id', 'amount_total', 'invoice_status'], 'limit': 1}
    )
    
    if not oc:
        print(f"❌ {oc_name} no encontrada\n")
        continue
    
    oc = oc[0]
    oc_id = oc['id']
    
    print(f"\n📋 INFORMACIÓN GENERAL")
    print(f"   ID: {oc_id}")
    print(f"   Proveedor: {oc['partner_id'][1] if oc['partner_id'] else 'N/A'}")
    print(f"   Fecha: {oc['date_order']}")
    print(f"   Estado: {oc['state']}")
    print(f"   Estado facturación: {oc['invoice_status']}")
    print(f"   Moneda: {oc['currency_id'][1] if oc['currency_id'] else 'N/A'}")
    print(f"   Total OC: ${oc['amount_total']:,.2f}")
    
    detalle_oc['estado'] = oc['state']
    detalle_oc['moneda'] = oc['currency_id'][1] if oc['currency_id'] else 'N/A'
    detalle_oc['total_oc'] = oc['amount_total']
    detalle_oc['proveedor'] = oc['partner_id'][1] if oc['partner_id'] else 'N/A'
    
    # ========== PASO 2: LÍNEAS DE COMPRA ==========
    lineas = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
        [[['order_id', '=', oc_id]]],
        {'fields': ['id', 'product_id', 'product_qty', 'qty_received', 'qty_invoiced', 'price_unit', 'price_subtotal']}
    )
    
    print(f"\n📦 LÍNEAS DE COMPRA ({len(lineas)})")
    detalle_oc['lineas'] = []
    
    for linea in lineas:
        print(f"   └─ Línea ID {linea['id']}: {linea['product_id'][1] if linea['product_id'] else 'N/A'}")
        print(f"      Cantidad: {linea['product_qty']:,.3f} | Recibida: {linea.get('qty_received', 0):,.3f} | Facturada: {linea.get('qty_invoiced', 0):,.3f}")
        print(f"      Precio unitario: ${linea['price_unit']:,.2f}")
        print(f"      Subtotal: ${linea['price_subtotal']:,.2f}")
        
        detalle_oc['lineas'].append({
            'id': linea['id'],
            'producto': linea['product_id'][1] if linea['product_id'] else 'N/A',
            'cantidad': linea['product_qty'],
            'recibida': linea.get('qty_received', 0),
            'facturada': linea.get('qty_invoiced', 0),
            'precio_unit': linea['price_unit'],
            'subtotal': linea['price_subtotal']
        })
    
    # ========== PASO 3: RECEPCIONES ==========
    pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read',
        [[['origin', '=', oc_name]]],
        {'fields': ['id', 'name', 'state', 'date_done', 'picking_type_id']}
    )
    
    print(f"\n📦 RECEPCIONES ({len(pickings)})")
    detalle_oc['recepciones'] = []
    
    total_movimientos = 0
    for picking in pickings:
        print(f"   └─ {picking['name']} (ID: {picking['id']})")
        print(f"      Estado: {picking['state']} | Fecha: {picking.get('date_done', 'N/A')}")
        
        # Movimientos de inventario
        moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
            [[['picking_id', '=', picking['id']]]],
            {'fields': ['id', 'product_id', 'product_uom_qty', 'quantity_done', 'state', 'purchase_line_id']}
        )
        
        total_movimientos += len(moves)
        movimientos_detalle = []
        
        for move in moves:
            if move['product_id']:
                print(f"      ├─ Mov ID {move['id']}: {move['product_id'][1][:50]}")
                print(f"      │  Cantidad: {move['product_uom_qty']:,.3f} | Realizada: {move['quantity_done']:,.3f} | Estado: {move['state']}")
                
                movimientos_detalle.append({
                    'id': move['id'],
                    'producto': move['product_id'][1],
                    'cantidad': move['product_uom_qty'],
                    'realizada': move['quantity_done']
                })
        
        detalle_oc['recepciones'].append({
            'id': picking['id'],
            'nombre': picking['name'],
            'estado': picking['state'],
            'movimientos': movimientos_detalle
        })
    
    print(f"   Total movimientos: {total_movimientos}")
    
    # ========== PASO 4: VALORACIÓN DE INVENTARIO ==========
    valuation_layers = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'search_read',
        [[['description', 'ilike', oc_name]]],
        {'fields': ['id', 'description', 'quantity', 'unit_cost', 'value', 'product_id', 'stock_move_id'], 'limit': 20}
    )
    
    print(f"\n💰 CAPAS DE VALORACIÓN DE INVENTARIO ({len(valuation_layers)})")
    detalle_oc['valoracion'] = []
    total_valor_inventario = 0
    
    for layer in valuation_layers:
        print(f"   └─ Capa ID {layer['id']}: {layer['description'][:60]}")
        print(f"      Producto: {layer['product_id'][1] if layer['product_id'] else 'N/A'}")
        print(f"      Cantidad: {layer['quantity']:,.3f} | Costo unitario: ${layer['unit_cost']:,.2f}")
        print(f"      Valor total: ${layer['value']:,.2f}")
        
        total_valor_inventario += layer['value']
        
        detalle_oc['valoracion'].append({
            'id': layer['id'],
            'cantidad': layer['quantity'],
            'costo_unitario': layer['unit_cost'],
            'valor': layer['value']
        })
    
    if valuation_layers:
        print(f"   Total valor en inventario: ${total_valor_inventario:,.2f}")
        detalle_oc['total_valor_inventario'] = total_valor_inventario
    
    # ========== PASO 5: FACTURAS ==========
    # Buscar facturas relacionadas
    facturas = models.execute_kw(db, uid, password, 'account.move', 'search_read',
        [[['ref', 'ilike', oc_name], ['move_type', 'in', ['in_invoice', 'in_refund']]]],
        {'fields': ['id', 'name', 'ref', 'state', 'invoice_date', 'amount_total', 'currency_id'], 'limit': 10}
    )
    
    print(f"\n🧾 FACTURAS ({len(facturas)})")
    detalle_oc['facturas'] = []
    total_facturado = 0
    
    for factura in facturas:
        print(f"   └─ {factura['name']} (ID: {factura['id']})")
        print(f"      Ref: {factura.get('ref', 'N/A')} | Estado: {factura['state']}")
        print(f"      Fecha: {factura.get('invoice_date', 'N/A')}")
        print(f"      Monto: ${factura['amount_total']:,.2f} {factura['currency_id'][1] if factura['currency_id'] else ''}")
        
        if factura['state'] == 'posted':
            total_facturado += factura['amount_total']
        
        detalle_oc['facturas'].append({
            'id': factura['id'],
            'nombre': factura['name'],
            'estado': factura['state'],
            'monto': factura['amount_total']
        })
    
    if facturas:
        print(f"   Total facturado (posted): ${total_facturado:,.2f}")
        detalle_oc['total_facturado'] = total_facturado
    
    # ========== RESUMEN DE IMPACTO ==========
    print(f"\n📊 RESUMEN DE IMPACTO")
    print(f"   ✓ Líneas de compra actualizadas: {len(lineas)}")
    print(f"   ✓ Recepciones procesadas: {len(pickings)}")
    print(f"   ✓ Movimientos de inventario: {total_movimientos}")
    print(f"   ✓ Capas de valoración: {len(valuation_layers)}")
    print(f"   ✓ Facturas relacionadas: {len(facturas)}")
    
    if valuation_layers:
        print(f"   💰 Valor en inventario: ${total_valor_inventario:,.2f}")
        total_impacto_monetario += total_valor_inventario
    
    detalle_oc['impacto']['lineas_actualizadas'] = len(lineas)
    detalle_oc['impacto']['recepciones'] = len(pickings)
    detalle_oc['impacto']['movimientos'] = total_movimientos
    detalle_oc['impacto']['valoraciones'] = len(valuation_layers)
    detalle_oc['impacto']['facturas'] = len(facturas)
    
    resumen_general['detalles'][oc_name] = detalle_oc
    
    print(f"\n{'─' * 120}\n")

# ========== RESUMEN GENERAL FINAL ==========
print("=" * 120)
print(" " * 40 + "RESUMEN GENERAL FINAL")
print("=" * 120)

print(f"\n📊 ESTADÍSTICAS GLOBALES:")
print(f"   Total OCs corregidas: {len(OCS_CORREGIDAS)}")

total_lineas = sum(len(d.get('lineas', [])) for d in resumen_general['detalles'].values())
total_recepciones = sum(len(d.get('recepciones', [])) for d in resumen_general['detalles'].values())
total_valoraciones = sum(d['impacto'].get('valoraciones', 0) for d in resumen_general['detalles'].values())
total_facturas = sum(d['impacto'].get('facturas', 0) for d in resumen_general['detalles'].values())

print(f"   Total líneas actualizadas: {total_lineas}")
print(f"   Total recepciones: {total_recepciones}")
print(f"   Total capas de valoración: {total_valoraciones}")
print(f"   Total facturas relacionadas: {total_facturas}")
print(f"   💰 Impacto monetario total en inventario: ${total_impacto_monetario:,.2f}")

resumen_general['estadisticas'] = {
    'total_lineas': total_lineas,
    'total_recepciones': total_recepciones,
    'total_valoraciones': total_valoraciones,
    'total_facturas': total_facturas,
    'impacto_monetario': total_impacto_monetario
}

print(f"\n✅ VERIFICACIÓN POR OC:")
for oc_name, detalle in resumen_general['detalles'].items():
    estado = "✓" if detalle['estado'] == 'purchase' else "⚠️"
    print(f"   {estado} {oc_name}: ${detalle['total_oc']:,.2f} {detalle['moneda']} - Estado: {detalle['estado']}")

# Guardar reporte completo
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
reporte_file = f'REPORTE_COMPLETO_OCs_{timestamp}.json'

with open(reporte_file, 'w', encoding='utf-8') as f:
    json.dump(resumen_general, f, indent=2, ensure_ascii=False)

print(f"\n💾 Reporte completo guardado: {reporte_file}")

print("\n" + "=" * 120)
print(" " * 35 + "✅ ANÁLISIS COMPLETADO")
print("=" * 120)
