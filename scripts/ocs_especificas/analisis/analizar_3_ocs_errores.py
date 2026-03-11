#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis de 3 OCs con errores de precio y/o moneda:
- OC12902: precio debe ser 3.085 (no 3.080)
- OC09581: precio 2.3 en CLP debe cambiar a USD
- OC12363: precio 1.6 en CLP debe cambiar a USD
"""
import xmlrpc.client

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

print("=" * 100)
print("ANÁLISIS DE 3 OCs CON ERRORES DE PRECIO/MONEDA")
print("=" * 100)

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"\n✅ Conectado\n")

OCS_ANALIZAR = [
    {'nombre': 'OC12902', 'problema': 'Precio debe ser 3.085 (no 3.080)', 'precio_correcto': 3.085},
    {'nombre': 'OC09581', 'problema': 'Precio 2.3 en CLP, debe ser USD', 'precio_correcto': 2.3},
    {'nombre': 'OC12363', 'problema': 'Precio 1.6 en CLP, debe ser USD', 'precio_correcto': 1.6}
]

resultados = []

for oc_info in OCS_ANALIZAR:
    print("\n" + "=" * 100)
    print(f"ANALIZANDO: {oc_info['nombre']}")
    print(f"PROBLEMA: {oc_info['problema']}")
    print("=" * 100)
    
    # Buscar OC
    oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
        [[['name', '=', oc_info['nombre']]]],
        {'fields': [
            'id', 'name', 'partner_id', 'state', 'amount_total',
            'currency_id', 'invoice_status', 'invoice_ids', 'picking_ids'
        ], 'limit': 1}
    )
    
    if not oc:
        print(f"\n❌ {oc_info['nombre']} no encontrada")
        continue
    
    oc = oc[0]
    oc_id = oc['id']
    
    print(f"\n📋 OC: {oc['name']} (ID: {oc_id})")
    print(f"   Proveedor: {oc['partner_id'][1] if oc['partner_id'] else 'N/A'}")
    print(f"   Estado: {oc['state']}")
    print(f"   Moneda: {oc['currency_id'][1] if oc['currency_id'] else 'N/A'} {'⚠️' if 'CLP' in str(oc.get('currency_id', '')) else '✓'}")
    print(f"   Total: ${oc['amount_total']:,.2f}")
    print(f"   Estado Facturación: {oc.get('invoice_status', 'N/A')}")
    
    # Líneas de OC
    lineas = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
        [[['order_id', '=', oc_id]]],
        {'fields': [
            'id', 'product_id', 'product_qty', 'price_unit',
            'qty_received', 'qty_invoiced', 'currency_id'
        ]}
    )
    
    print(f"\n   LÍNEAS ({len(lineas)}):")
    for i, linea in enumerate(lineas, 1):
        print(f"   {i}. {linea['product_id'][1] if linea['product_id'] else 'N/A'}")
        print(f"      Cantidad: {linea['product_qty']} kg")
        print(f"      Precio: ${linea['price_unit']:,.2f} {'⚠️' if abs(linea['price_unit'] - oc_info['precio_correcto']) > 0.01 else '✓'}")
        print(f"      Recibido: {linea['qty_received']}, Facturado: {linea['qty_invoiced']}")
    
    # Verificar facturas
    tiene_facturas = len(oc.get('invoice_ids', [])) > 0
    tiene_recepciones = len(oc.get('picking_ids', [])) > 0
    
    print(f"\n   ⚠️  Facturas: {'SÍ' if tiene_facturas else 'NO'}")
    print(f"   ⚠️  Recepciones: {'SÍ' if tiene_recepciones else 'NO'}")
    
    # Analizar moneda
    moneda_actual = oc['currency_id'][1] if oc['currency_id'] else 'N/A'
    necesita_cambio_moneda = 'CLP' in moneda_actual
    
    resultados.append({
        'oc': oc_info['nombre'],
        'oc_id': oc_id,
        'problema': oc_info['problema'],
        'precio_correcto': oc_info['precio_correcto'],
        'moneda_actual': moneda_actual,
        'necesita_cambio_moneda': necesita_cambio_moneda,
        'tiene_facturas': tiene_facturas,
        'tiene_recepciones': tiene_recepciones,
        'lineas': lineas,
        'estado': oc['state']
    })

# ============================================================================
# RESUMEN Y PLAN
# ============================================================================
print("\n" + "=" * 100)
print("RESUMEN Y PLAN DE CORRECCIÓN")
print("=" * 100)

for res in resultados:
    print(f"\n{res['oc']}:")
    print(f"   Problema: {res['problema']}")
    print(f"   Precio correcto: ${res['precio_correcto']}")
    print(f"   Moneda actual: {res['moneda_actual']}")
    print(f"   Cambiar a USD: {'SÍ ⚠️' if res['necesita_cambio_moneda'] else 'NO'}")
    print(f"   Facturas: {'SÍ ⚠️' if res['tiene_facturas'] else 'NO ✓'}")
    print(f"   Recepciones: {'SÍ' if res['tiene_recepciones'] else 'NO'}")
    print(f"   Líneas a corregir: {len(res['lineas'])}")
    
    complejidad = "SIMPLE" if not res['tiene_facturas'] else "COMPLEJA"
    print(f"   Complejidad: {complejidad}")

print("\n" + "=" * 100)
print("SIGUIENTE PASO: Crear script de ejecución según complejidad")
print("=" * 100)
