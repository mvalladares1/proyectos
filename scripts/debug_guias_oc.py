#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug: Rastrear Albaranes y Guías de Despacho desde OCs
Objetivo: Encontrar la guía de despacho (x_studio_gua_de_despacho) de los albaranes
asociados a cada OC, excluyendo albaranes con devolución.
"""
import xmlrpc.client

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# OCs a analizar
OCS_NOMBRES = [
    "OC08970", "OC09397", "OC09396", "OC09442", "OC09420", "OC09418",
    "OC09888", "OC09885", "OC10053", "OC10251", "OC10151", "OC10447"
]

common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

print("\n" + "="*100)
print("DEBUG: RASTREO OC → ALBARÁN → GUÍA DE DESPACHO")
print("="*100)

# 1. Buscar las OCs
print("\n1. BUSCANDO OCs:")
print("-" * 100)

ocs = models.execute_kw(
    DB, uid, PASSWORD,
    'purchase.order', 'search_read',
    [[['name', 'in', OCS_NOMBRES]]],
    {'fields': ['id', 'name', 'partner_id', 'picking_ids', 'date_order', 'order_line']}
)

print(f"  Encontradas: {len(ocs)} OCs")

# 2. Analizar cada OC
print("\n2. ANÁLISIS POR OC:")
print("-" * 100)

resultados = []

for oc in sorted(ocs, key=lambda x: x['name']):
    print(f"\n  📦 {oc['name']}:")
    
    proveedor = oc.get('partner_id', [None, 'N/A'])
    proveedor_nombre = proveedor[1] if isinstance(proveedor, (list, tuple)) else proveedor
    print(f"     Proveedor: {proveedor_nombre}")
    
    picking_ids = oc.get('picking_ids', [])
    print(f"     Albaranes asociados (picking_ids): {picking_ids}")
    
    if not picking_ids:
        print(f"     ⚠️ Sin albaranes asociados directamente")
        
        # Intentar buscar por origin (nombre de OC)
        pickings_by_origin = models.execute_kw(
            DB, uid, PASSWORD,
            'stock.picking', 'search_read',
            [[['origin', 'ilike', oc['name']]]],
            {'fields': ['id', 'name', 'origin', 'x_studio_gua_de_despacho', 'state', 'picking_type_id']}
        )
        
        if pickings_by_origin:
            print(f"     → Encontrados por origin: {len(pickings_by_origin)}")
            for p in pickings_by_origin:
                print(f"        - {p['name']}: guía={p.get('x_studio_gua_de_despacho', 'N/A')}, estado={p['state']}")
                picking_ids.append(p['id'])
    
    # 3. Buscar detalles de los albaranes
    if picking_ids:
        pickings = models.execute_kw(
            DB, uid, PASSWORD,
            'stock.picking', 'search_read',
            [[['id', 'in', picking_ids]]],
            {'fields': ['id', 'name', 'origin', 'x_studio_gua_de_despacho', 'state', 
                       'picking_type_id', 'partner_id', 'date_done', 'scheduled_date']}
        )
        
        print(f"     Detalles de albaranes:")
        
        for p in pickings:
            guia = p.get('x_studio_gua_de_despacho', '')
            tipo = p.get('picking_type_id', [None, 'N/A'])
            tipo_nombre = tipo[1] if isinstance(tipo, (list, tuple)) else tipo
            
            # Verificar si tiene devolución
            devoluciones = models.execute_kw(
                DB, uid, PASSWORD,
                'stock.picking', 'search_read',
                [[['origin', 'ilike', p['name']],  # Devoluciones referencian al picking original
                  ['picking_type_id', 'in', [2, 3, 5]]]],  # Tipos de devolución
                {'fields': ['id', 'name', 'state']}
            )
            
            tiene_devolucion = len(devoluciones) > 0
            estado_dev = f"⚠️ DEVOLUCIÓN: {[d['name'] for d in devoluciones]}" if tiene_devolucion else "✅ Sin devolución"
            
            print(f"        - {p['name']}:")
            print(f"           Tipo: {tipo_nombre}")
            print(f"           Guía Despacho: {guia or '(vacío)'}")
            print(f"           Estado: {p['state']}")
            print(f"           {estado_dev}")
            
            if not tiene_devolucion and guia:
                resultados.append({
                    'oc': oc['name'],
                    'albaran': p['name'],
                    'guia_despacho': guia,
                    'estado': p['state']
                })

# 3. Ver campos disponibles en stock.picking
print("\n3. CAMPOS RELACIONADOS CON GUÍA EN stock.picking:")
print("-" * 100)

# Buscar campos que contengan "gui" o "despacho"
campos = models.execute_kw(
    DB, uid, PASSWORD,
    'ir.model.fields', 'search_read',
    [[['model', '=', 'stock.picking'], 
      '|', '|', '|',
      ['name', 'ilike', 'gui'],
      ['name', 'ilike', 'despacho'],
      ['name', 'ilike', 'studio'],
      ['name', 'ilike', 'guia']]],
    {'fields': ['name', 'field_description', 'ttype']}
)

for c in campos:
    print(f"  - {c['name']}: {c['field_description']} ({c['ttype']})")

# 4. Buscar un picking de ejemplo con datos completos
print("\n4. EJEMPLO DE PICKING CON GUÍA DE DESPACHO:")
print("-" * 100)

# Buscar un picking que tenga guía de despacho
picking_ejemplo = models.execute_kw(
    DB, uid, PASSWORD,
    'stock.picking', 'search_read',
    [[['x_studio_gua_de_despacho', '!=', False], 
      ['x_studio_categora_de_producto', '=', 'MP']]],
    {'fields': ['id', 'name', 'origin', 'x_studio_gua_de_despacho', 'state', 'partner_id'],
     'limit': 5}
)

for p in picking_ejemplo:
    print(f"  {p['name']} - Guía: {p.get('x_studio_gua_de_despacho')} - Origin: {p.get('origin')}")

# 5. Buscar por líneas de OC → move lines → picking
print("\n5. ALTERNATIVA: OC → LINEAS → STOCK.MOVE → PICKING:")
print("-" * 100)

for oc_name in OCS_NOMBRES[:3]:  # Solo las primeras 3 para debug
    print(f"\n  {oc_name}:")
    
    # Buscar OC
    oc = models.execute_kw(
        DB, uid, PASSWORD,
        'purchase.order', 'search_read',
        [[['name', '=', oc_name]]],
        {'fields': ['id', 'name', 'order_line']}
    )
    
    if not oc:
        print(f"    OC no encontrada")
        continue
    
    oc = oc[0]
    
    # Buscar líneas de OC
    lineas = models.execute_kw(
        DB, uid, PASSWORD,
        'purchase.order.line', 'search_read',
        [[['order_id', '=', oc['id']]]],
        {'fields': ['id', 'product_id', 'move_ids', 'qty_received']}
    )
    
    print(f"    Líneas: {len(lineas)}")
    
    for linea in lineas:
        move_ids = linea.get('move_ids', [])
        if move_ids:
            # Buscar los moves
            moves = models.execute_kw(
                DB, uid, PASSWORD,
                'stock.move', 'search_read',
                [[['id', 'in', move_ids]]],
                {'fields': ['id', 'picking_id', 'state', 'quantity_done']}
            )
            
            for move in moves:
                picking_id = move.get('picking_id')
                if picking_id:
                    picking_id_val = picking_id[0] if isinstance(picking_id, (list, tuple)) else picking_id
                    
                    # Obtener picking con guía
                    picking = models.execute_kw(
                        DB, uid, PASSWORD,
                        'stock.picking', 'read',
                        [[picking_id_val]],
                        {'fields': ['name', 'x_studio_gua_de_despacho', 'state']}
                    )
                    
                    if picking:
                        p = picking[0]
                        print(f"      → Picking: {p['name']}, Guía: {p.get('x_studio_gua_de_despacho', 'N/A')}, Estado: {p['state']}")

# Resumen
print("\n" + "="*100)
print("RESUMEN: ALBARANES SIN DEVOLUCIÓN CON GUÍA")
print("="*100)

if resultados:
    for r in resultados:
        print(f"  {r['oc']} → {r['albaran']} → Guía: {r['guia_despacho']} ({r['estado']})")
else:
    print("  No se encontraron albaranes con guía de despacho sin devolución")

print("\n✅ Debug completado")
