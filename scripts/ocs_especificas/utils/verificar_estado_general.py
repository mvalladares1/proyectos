#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICACIÓN GENERAL DE OCs CORREGIDAS
Verificar el estado actual de todas las OCs que han sido corregidas
"""
import xmlrpc.client
import json
from datetime import datetime

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# OCs corregidas - Actualizar esta lista cuando se corrijan nuevas OCs
OCS_CORREGIDAS = {
    'OC12288': {'precio_esperado': 2.0},
    'OC11401': {'precio_esperado': 1.6},
    'OC12902': {'precio_esperado': 3085.0},
    'OC09581': {'precio_esperado': 2.3},
    'OC12755': {'precio_esperado': 2000.0},
    'OC13491': {'precio_esperado': 3300.0},
    'OC13530': {'precio_esperado': 3300.0},
    'OC13596': {'precio_esperado': 3300.0},
    'OC13708': {'precio_esperado': 3300.0},
    'OC09397': {'precio_esperado': 2850.0},
    'OC10388': {'precio_esperado': 2850.0},
    'OC10053': {'precio_esperado': 2850.0}
}

print("=" * 120)
print("VERIFICACIÓN GENERAL DE OCs CORREGIDAS")
print(f"Total OCs a verificar: {len(OCS_CORREGIDAS)}")
print("=" * 120)

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"\n✅ Conectado\n")

resultados = {
    'fecha_verificacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'ocs': {},
    'problemas': []
}

for oc_name, config in OCS_CORREGIDAS.items():
    print("=" * 120)
    print(f"OC: {oc_name}")
    print("=" * 120)
    
    precio_esperado = config['precio_esperado']
    
    # Buscar OC
    oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
        [[['name', '=', oc_name]]],
        {'fields': ['id', 'state', 'currency_id', 'amount_total', 'invoice_status'], 'limit': 1}
    )
    
    if not oc:
        print(f"❌ {oc_name} no encontrada\n")
        resultados['problemas'].append({
            'oc': oc_name,
            'tipo': 'OC_NO_ENCONTRADA'
        })
        continue
    
    oc = oc[0]
    oc_id = oc['id']
    
    print(f"📋 Estado: {oc['state']}")
    print(f"💰 Total: ${oc['amount_total']:,.2f} {oc['currency_id'][1] if oc['currency_id'] else 'N/A'}")
    print(f"🧾 Facturación: {oc['invoice_status']}")
    
    oc_resultado = {
        'estado': oc['state'],
        'total': oc['amount_total'],
        'moneda': oc['currency_id'][1] if oc['currency_id'] else 'N/A',
        'facturacion': oc['invoice_status'],
        'problemas': []
    }
    
    # Verificar líneas
    lineas = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
        [[['order_id', '=', oc_id]]],
        {'fields': ['id', 'product_id', 'price_unit', 'product_qty', 'qty_received']}
    )
    
    print(f"\n📦 Líneas de compra:")
    for linea in lineas:
        precio_linea = linea['price_unit']
        correcto = abs(precio_linea - precio_esperado) < 0.01
        estado = "✓" if correcto else "❌"
        
        print(f"   {estado} Línea {linea['id']}: ${precio_linea:,.2f} (esperado: ${precio_esperado:,.2f})")
        
        if not correcto:
            oc_resultado['problemas'].append({
                'tipo': 'LINEA_PRECIO_INCORRECTO',
                'linea_id': linea['id'],
                'precio_actual': precio_linea,
                'precio_esperado': precio_esperado
            })
    
    # Verificar movimientos
    pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read',
        [[['origin', '=', oc_name], ['state', '=', 'done']]],
        {'fields': ['id', 'name']}
    )
    
    print(f"\n📦 Movimientos de stock:")
    for picking in pickings:
        moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
            [[['picking_id', '=', picking['id']], ['quantity_done', '>', 0]]],
            {'fields': ['id', 'product_id', 'price_unit', 'quantity_done']}
        )
        
        for move in moves:
            # Verificar solo si es el producto principal (puede haber otros productos como bandejas)
            precio_move = move.get('price_unit', 0)
            
            # Tolerancia: verificar que esté "cerca" del precio esperado o sea 0
            if precio_move > 0:
                correcto = abs(precio_move - precio_esperado) < 0.01
                estado = "✓" if correcto else "❌"
                
                if move['product_id']:
                    producto = move['product_id'][1][:50]
                    print(f"   {estado} Move {move['id']}: ${precio_move:,.2f} ({producto})")
                    
                    if not correcto and precio_move != 0:
                        oc_resultado['problemas'].append({
                            'tipo': 'MOVE_PRECIO_INCORRECTO',
                            'move_id': move['id'],
                            'precio_actual': precio_move,
                            'precio_esperado': precio_esperado
                        })
    
    # Verificar capas de valoración
    print(f"\n💰 Capas de valoración:")
    capas_encontradas = 0
    
    for picking in pickings:
        moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
            [[['picking_id', '=', picking['id']], ['quantity_done', '>', 0]]],
            {'fields': ['id']}
        )
        
        for move in moves:
            layers = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'search_read',
                [[['stock_move_id', '=', move['id']]]],
                {'fields': ['id', 'unit_cost', 'value', 'quantity']}
            )
            
            for layer in layers:
                capas_encontradas += 1
                costo = layer['unit_cost']
                correcto = abs(costo - precio_esperado) < 0.01
                estado = "✓" if correcto else "❌"
                
                print(f"   {estado} Layer {layer['id']}: Costo ${costo:,.2f}, Valor ${layer['value']:,.2f}")
                
                if not correcto and costo != 0:
                    oc_resultado['problemas'].append({
                        'tipo': 'LAYER_COSTO_INCORRECTO',
                        'layer_id': layer['id'],
                        'costo_actual': costo,
                        'costo_esperado': precio_esperado
                    })
    
    if capas_encontradas == 0:
        print(f"   ⚠️  No se encontraron capas de valoración")
    
    # Resumen de esta OC
    if oc_resultado['problemas']:
        print(f"\n❌ PROBLEMAS DETECTADOS: {len(oc_resultado['problemas'])}")
        for problema in oc_resultado['problemas']:
            print(f"   - {problema['tipo']}")
            resultados['problemas'].append({
                'oc': oc_name,
                **problema
            })
    else:
        print(f"\n✅ SIN PROBLEMAS")
    
    resultados['ocs'][oc_name] = oc_resultado
    print()

# RESUMEN GENERAL
print("=" * 120)
print("RESUMEN GENERAL")
print("=" * 120)

total_problemas = len(resultados['problemas'])

if total_problemas == 0:
    print(f"\n✅ TODAS LAS OCs ESTÁN CORRECTAS")
    print(f"   {len(OCS_CORREGIDAS)} OCs verificadas")
    print(f"   0 problemas encontrados")
else:
    print(f"\n⚠️  SE ENCONTRARON {total_problemas} PROBLEMAS:")
    
    # Agrupar por tipo
    problemas_por_tipo = {}
    for p in resultados['problemas']:
        tipo = p['tipo']
        problemas_por_tipo[tipo] = problemas_por_tipo.get(tipo, 0) + 1
    
    for tipo, cantidad in problemas_por_tipo.items():
        print(f"   - {tipo}: {cantidad}")
    
    print(f"\n   Detalles:")
    for p in resultados['problemas']:
        print(f"   • {p['oc']}: {p['tipo']}")

# Estado por OC
print(f"\n📊 ESTADO POR OC:")
for oc_name, resultado in resultados['ocs'].items():
    estado = "✓" if not resultado['problemas'] else "❌"
    print(f"   {estado} {oc_name}: ${resultado['total']:,.2f} {resultado['moneda']}")

# Guardar reporte
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
reporte_file = f'verificacion_general_{timestamp}.json'

with open(reporte_file, 'w', encoding='utf-8') as f:
    json.dump(resultados, f, indent=2, ensure_ascii=False)

print(f"\n💾 Reporte guardado: {reporte_file}")

print("\n" + "=" * 120)
if total_problemas == 0:
    print("✅ VERIFICACIÓN COMPLETADA - TODO CORRECTO")
else:
    print(f"⚠️  VERIFICACIÓN COMPLETADA - {total_problemas} PROBLEMAS DETECTADOS")
print("=" * 120)
