#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Investigar FAC 000011 relacionada con OC12288
"""
import xmlrpc.client

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

print("=" * 100)
print("INVESTIGAR FACTURA FAC 000011 - RELACIÓN CON OC12288")
print("=" * 100)

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"\n✅ Conectado\n")

# Buscar la factura
factura = models.execute_kw(db, uid, password, 'account.move', 'search_read',
    [[['name', '=', 'FAC 000011']]],
    {'fields': [
        'id', 'name', 'ref', 'state', 'move_type', 'invoice_date',
        'partner_id', 'amount_total', 'invoice_line_ids', 
        'invoice_origin', 'purchase_id'
    ], 'limit': 1}
)

if not factura:
    print("❌ Factura FAC 000011 no encontrada")
    exit(1)

factura = factura[0]

print(f"FACTURA: {factura['name']}")
print(f"  ID: {factura['id']}")
print(f"  Estado: {factura['state']} {'✓ (borrador, se puede modificar)' if factura['state'] == 'draft' else '⚠️ (contabilizada)'}")
print(f"  Tipo: {factura['move_type']}")
print(f"  Referencia: {factura.get('ref', 'N/A')}")
print(f"  Origen: {factura.get('invoice_origin', 'N/A')}")
print(f"  Proveedor: {factura['partner_id'][1] if factura['partner_id'] else 'N/A'}")
print(f"  Total: ${factura['amount_total']:,.2f}")
print(f"  OC Relacionada: {factura['purchase_id'][1] if factura.get('purchase_id') else 'N/A'}")

# Obtener líneas de factura
print(f"\nLÍNEAS DE FACTURA:")
print("=" * 100)

if factura.get('invoice_line_ids'):
    lineas = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
        [[['id', 'in', factura['invoice_line_ids']]]],
        {'fields': [
            'id', 'product_id', 'name', 'quantity', 'price_unit',
            'price_subtotal', 'price_total', 'purchase_line_id'
        ]}
    )
    
    print(f"\nEncontradas {len(lineas)} líneas:\n")
    
    tiene_oc12288 = False
    for i, linea in enumerate(lineas, 1):
        print(f"Línea #{i}:")
        print(f"  Producto: {linea['product_id'][1] if linea['product_id'] else 'N/A'}")
        print(f"  Cantidad: {linea['quantity']}")
        print(f"  Precio Unit: ${linea['price_unit']:,.2f}")
        print(f"  Subtotal: ${linea['price_subtotal']:,.2f}")
        print(f"  Total: ${linea['price_total']:,.2f}")
        
        if linea.get('purchase_line_id'):
            # Buscar la línea de OC
            pol = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
                [[['id', '=', linea['purchase_line_id'][0]]]],
                {'fields': ['order_id']}
            )
            if pol:
                oc_relacionada = pol[0]['order_id'][1] if pol[0].get('order_id') else 'N/A'
                print(f"  OC Relacionada: {oc_relacionada}")
                if 'OC12288' in str(oc_relacionada):
                    tiene_oc12288 = True
                    print(f"  ⚠️  ESTA LÍNEA ESTÁ RELACIONADA CON OC12288")
        print()
    
    if tiene_oc12288:
        print("\n⚠️  ADVERTENCIA: Esta factura contiene líneas de OC12288")
        print("   Si se corrige el precio de OC12288, habrá que:")
        print("   1. Eliminar/Ajustar esta factura borrador")
        print("   2. O actualizarla después de corregir la OC")
    else:
        print("\n✓ Esta factura NO contiene líneas de OC12288")
        print("  La corrección de OC12288 no afectará esta factura")

print("\n" + "=" * 100)
