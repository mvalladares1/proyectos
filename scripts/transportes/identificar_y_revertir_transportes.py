#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplemente revisar los productos y proveedores para identificar TRANSPORTES
"""
import xmlrpc.client

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

FRANCISCO_ID = 258

common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

print("\n" + "="*80)
print("IDENTIFICAR OCs DE TRANSPORTES vs OTRAS")
print("="*80)

# Comparar OC12393 vs OC12384
ocs = [('OC12393', 'TRANSPORTES'), ('OC12384', 'CALIDAD')]

for oc_name, tipo in ocs:
    print(f"\n{oc_name} ({tipo}):")
    print("-" * 80)
    
    oc = models.execute_kw(
        DB, uid, PASSWORD,
        'purchase.order', 'search_read',
        [[['name', '=', oc_name]]],
        {'fields': ['id', 'name', 'partner_id']}
    )
    
    if oc:
        oc_id = oc[0]['id']
        proveedor = oc[0]['partner_id'][1] if oc[0].get('partner_id') else ''
        print(f"  Proveedor: {proveedor}")
        
        # Ver productos
        lineas = models.execute_kw(
            DB, uid, PASSWORD,
            'purchase.order.line', 'search_read',
            [[['order_id', '=', oc_id]]],
            {'fields': ['product_id'], 'limit': 5}
        )
        
        print(f"  Productos:")
        for linea in lineas:
            if linea.get('product_id'):
                prod_name = linea['product_id'][1] if isinstance(linea['product_id'], (list, tuple)) else ''
                print(f"    - {prod_name}")

# Criterio: Si el producto contiene "FLETE" o proveedor contiene "TRANSPORTE"
print("\n" + "="*80)
print("CRITERIO IDENTIFICADO:")
print("="*80)
print("""
OCs de TRANSPORTES tienen:
- Productos con nombre que contiene: "FLETE", "TRANSPORTE"
- O proveedor que contiene: "TRANSPORTE", "ARRAYANES"

OCs de CALIDAD/OTRAS tienen:
- Productos de tipo: "AEROBIOS", "COLIFORMES", "MUESTRA"
- Proveedores de laboratorios o servicios diferentes
""")

# Ahora necesito revertir solo las OCs que NO son TRANSPORTES
print("\n" + "="*80)
print("REVERSAR CAMBIOS EN OCs NO-TRANSPORTES")
print("="*80)

# Buscar las 4 OCs que modifiqué
ocs_modificadas = ['OC12381', 'OC12312', 'OC12384', 'OC12383']

ocs_revertir = []

for oc_name in ocs_modificadas:
    oc = models.execute_kw(
        DB, uid, PASSWORD,
        'purchase.order', 'search_read',
        [[['name', '=', oc_name]]],
        {'fields': ['id', 'name', 'partner_id']}
    )
    
    if not oc:
        continue
    
    oc_id = oc[0]['id']
    proveedor = oc[0]['partner_id'][1] if oc[0].get('partner_id') else ''
    
    # Ver productos
    lineas = models.execute_kw(
        DB, uid, PASSWORD,
        'purchase.order.line', 'search_read',
        [[['order_id', '=', oc_id]]],
        {'fields': ['product_id'], 'limit': 1}
    )
    
    es_transporte = False
    if 'TRANSPORTE' in proveedor.upper() or 'ARRAYANES' in proveedor.upper():
        es_transporte = True
    
    if lineas and lineas[0].get('product_id'):
        prod_name = lineas[0]['product_id'][1] if isinstance(lineas[0]['product_id'], (list, tuple)) else ''
        if 'FLETE' in prod_name.upper() or 'TRANSPORTE' in prod_name.upper():
            es_transporte = True
    
    print(f"\n  {oc_name}:")
    print(f"    Proveedor: {proveedor}")
    if lineas:
        print(f"    Producto: {prod_name}")
    print(f"    Es TRANSPORTES: {'✓' if es_transporte else '✗'}")
    
    if not es_transporte:
        ocs_revertir.append((oc_id, oc_name))

# Revertir
print(f"\n\nOCs a revertir: {len(ocs_revertir)}")

for oc_id, oc_name in ocs_revertir:
    # Eliminar actividad de Francisco
    acts = models.execute_kw(
        DB, uid, PASSWORD,
        'mail.activity', 'search_read',
        [[['res_model', '=', 'purchase.order'],
          ['res_id', '=', oc_id],
          ['user_id', '=', FRANCISCO_ID]]],
        {'fields': ['id']}
    )
    
    if acts:
        try:
            models.execute_kw(
                DB, uid, PASSWORD,
                'mail.activity', 'unlink',
                [[act['id'] for act in acts]]
            )
            print(f"  ✅ {oc_name}: Actividad de Francisco eliminada")
        except Exception as e:
            print(f"  ✗ {oc_name}: Error - {str(e)[:50]}")

print("\n✅ Reversión completada")
