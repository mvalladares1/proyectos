#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Asignar Francisco a OC12393 y limpiar RFQs de SERVICIOS
"""
import xmlrpc.client

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

FRANCISCO_ID = 258
MAXIMO_ID = 241

print("\n" + "="*80)
print("LIMPIAR APROBADORES EN RFQs DE SERVICIOS")
print("="*80)

common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

# 1. Buscar modelo purchase.order
ir_model = models.execute_kw(
    DB, uid, PASSWORD,
    'ir.model', 'search_read',
    [[['model', '=', 'purchase.order']]],
    {'fields': ['id'], 'limit': 1}
)
res_model_id = ir_model[0]['id'] if ir_model else None

print(f"\n✓ res_model_id: {res_model_id}")

# 2. Buscar RFQs de SERVICIOS
print("\n1. BUSCANDO RFQs DE SERVICIOS:")
print("-" * 80)

rfqs = models.execute_kw(
    DB, uid, PASSWORD,
    'purchase.order', 'search_read',
    [[['state', 'in', ['draft', 'sent']], 
      ['x_studio_categora_de_producto', '=', 'SERVICIOS']]],
    {'fields': ['id', 'name', 'state'], 'limit': 20}
)

print(f"  Encontradas: {len(rfqs)} RFQs\n")

total_procesadas = 0
total_eliminadas = 0
total_creadas = 0

for rfq in rfqs:
    print(f"  {rfq['name']} (Estado: {rfq['state']})")
    
    # Buscar actividades
    actividades = models.execute_kw(
        DB, uid, PASSWORD,
        'mail.activity', 'search_read',
        [[['res_model', '=', 'purchase.order'], 
          ['res_id', '=', rfq['id']],
          ['activity_type_id', '=', 9]]],
        {'fields': ['id', 'user_id']}
    )
    
    if not actividades:
        print(f"    ℹ️  Sin actividades")
        continue
    
    print(f"    Actividades: {len(actividades)}")
    
    # Identificar cuáles eliminar
    actividades_eliminar = []
    tiene_francisco = False
    
    for act in actividades:
        user_id = act['user_id'][0] if isinstance(act['user_id'], (list, tuple)) else act['user_id']
        user_name = act['user_id'][1] if isinstance(act['user_id'], (list, tuple)) else ''
        
        if user_id == FRANCISCO_ID:
            tiene_francisco = True
            print(f"      ✓ Francisco")
        else:
            actividades_eliminar.append(act['id'])
            print(f"      ✗ {user_name[:30]}")
    
    # Eliminar incorrectas
    if actividades_eliminar:
        try:
            models.execute_kw(
                DB, uid, PASSWORD,
                'mail.activity', 'unlink',
                [actividades_eliminar]
            )
            print(f"    ✅ Eliminadas: {len(actividades_eliminar)}")
            total_eliminadas += len(actividades_eliminar)
        except Exception as e:
            print(f"    ✗ Error eliminando: {str(e)[:80]}")
            continue
    
    # Crear para Francisco si no existe
    if not tiene_francisco:
        try:
            nueva_act = models.execute_kw(
                DB, uid, PASSWORD,
                'mail.activity', 'create',
                [{
                    'res_model': 'purchase.order',
                    'res_model_id': res_model_id,
                    'res_id': rfq['id'],
                    'activity_type_id': 9,
                    'summary': 'Aprobación FRANCISCO - Transportes/Servicios',
                    'user_id': FRANCISCO_ID,
                    'note': '<p>Esta solicitud requiere aprobación de Francisco Luttecke.</p>'
                }]
            )
            print(f"    ✅ Creada actividad para Francisco (ID: {nueva_act})")
            total_creadas += 1
        except Exception as e:
            print(f"    ✗ Error creando: {str(e)[:80]}")
    
    total_procesadas += 1
    print()

print("\n" + "="*80)
print("RESUMEN")
print("="*80)
print(f"  RFQs encontradas: {len(rfqs)}")
print(f"  RFQs procesadas: {total_procesadas}")
print(f"  Actividades eliminadas: {total_eliminadas}")
print(f"  Actividades creadas para Francisco: {total_creadas}")
print(f"\n  ✅ COMPLETADO!")
print(f"  📋 Ahora Francisco puede aprobar las RFQs de TRANSPORTES sin bloqueos.")
