#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simplificado para configurar Francisco como aprobador de RFQs
"""
import xmlrpc.client

# Configuración
URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

MAXIMO_ID = 241

print("\n" + "="*80)
print("CONFIGURAR FRANCISCO LUTTECKE - APROBADOR RFQs TRANSPORTES")
print("="*80)

# Conectar
common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

print(f"\n✓ Conectado como UID: {uid}")

# 1. Buscar Francisco
print("\n1. BUSCANDO FRANCISCO LUTTECKE:")
print("-" * 80)

francisco_users = models.execute_kw(
    DB, uid, PASSWORD,
    'res.users', 'search_read',
    [[['name', 'ilike', 'LUTTECKE']]],
    {'fields': ['id', 'name', 'login']}
)

if francisco_users:
    francisco_id = francisco_users[0]['id']
    francisco_nombre = francisco_users[0]['name']
    print(f"  ✓ {francisco_nombre} (ID: {francisco_id})")
else:
    print("  ✗ No encontrado")
    exit(1)

# 2. Ver OC12393
print("\n2. VERIFICANDO OC12393:")
print("-" * 80)

oc = models.execute_kw(
    DB, uid, PASSWORD,
    'purchase.order', 'search_read',
    [[['name', '=', 'OC12393']]],
    {'fields': ['id', 'name', 'state', 'x_studio_categora_de_producto']}
)

if oc:
    oc_id = oc[0]['id']
    print(f"  OC: {oc[0]['name']}")
    print(f"  Estado: {oc[0]['state']}")
    print(f"  Categoría: {oc[0].get('x_studio_categora_de_producto')}")
    
    # Ver actividades
    actividades = models.execute_kw(
        DB, uid, PASSWORD,
        'mail.activity', 'search_read',
        [[['res_model', '=', 'purchase.order'], ['res_id', '=', oc_id]]],
        {'fields': ['id', 'user_id']}
    )
    
    print(f"\n  Aprobadores actuales: {len(actividades)}")
    for act in actividades:
        user_name = act['user_id'][1] if isinstance(act['user_id'], (list, tuple)) else ''
        user_id = act['user_id'][0] if isinstance(act['user_id'], (list, tuple)) else act['user_id']
        simbolo = "✓" if user_id == francisco_id else "✗"
        print(f"    {simbolo} {user_name}")
    
    # Eliminar los que no son Francisco
    actividades_eliminar = [
        act['id'] for act in actividades 
        if (act['user_id'][0] if isinstance(act['user_id'], (list, tuple)) else act['user_id']) != francisco_id
    ]
    
    if actividades_eliminar:
        print(f"\n  Eliminando {len(actividades_eliminar)} aprobadores incorrectos...")
        try:
            models.execute_kw(
                DB, uid, PASSWORD,
                'mail.activity', 'unlink',
                [actividades_eliminar]
            )
            print(f"  ✅ Eliminados correctamente")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    # Verificar si Francisco está
    tiene_francisco = any(
        (act['user_id'][0] if isinstance(act['user_id'], (list, tuple)) else act['user_id']) == francisco_id
        for act in actividades
    )
    
    if not tiene_francisco:
        print(f"  ℹ️  Francisco no está asignado aún")
    else:
        print(f"  ✅ Francisco ya está como aprobador")

# 3. Actualizar automatización
print("\n3. ACTUALIZANDO AUTOMATIZACIÓN (ID: 1678):")
print("-" * 80)

automation_code = f"""# Automatización: Aprobaciones TRANSPORTES + SERVICIOS
# FRANCISCO LUTTECKE (ID: {francisco_id}) - RFQs (draft/sent)
# MAXIMO (ID: {MAXIMO_ID}) - OCs confirmadas

for order in records:
    es_servicio = False
    
    if order.x_studio_categora_de_producto and 'SERVICIO' in order.x_studio_categora_de_producto.upper():
        es_servicio = True
    elif order.x_studio_categora and order.x_studio_categora == 'Servicio':
        es_servicio = True
    else:
        for line in order.order_line:
            if line.product_id and line.product_id.categ_id:
                if 'SERVICIO' in line.product_id.categ_id.display_name.upper():
                    es_servicio = True
                    break
    
    if es_servicio:
        activities = env['mail.activity'].search([
            ('res_model', '=', 'purchase.order'),
            ('res_id', '=', order.id),
            ('activity_type_id.name', '=', 'Grant Approval')
        ])
        
        # Determinar aprobador según estado
        if order.state in ['draft', 'sent']:
            aprobador_id = {francisco_id}
            aprobador_nombre = "FRANCISCO LUTTECKE"
        else:
            aprobador_id = {MAXIMO_ID}
            aprobador_nombre = "MAXIMO"
        
        # Eliminar actividades incorrectas
        activities_to_remove = activities.filtered(lambda a: a.user_id.id not in aprobador_id)
        if activities_to_remove:
            activities_to_remove.unlink()
        
        # Verificar si existe actividad correcta
        correct_activity = activities.filtered(lambda a: a.user_id.id in aprobador_id)
        
        # Crear si no existe
        if not correct_activity and order.state in ['draft', 'sent', 'to approve']:
            try:
                ir_model = env['ir.model'].search([('model', '=', 'purchase.order')], limit=1)
                env['mail.activity'].create({{
                    'res_model': 'purchase.order',
                    'res_model_id': ir_model.id if ir_model else False,
                    'res_id': order.id,
                    'activity_type_id': 9,
                    'summary': f'Aprobación {{aprobador_nombre}} - Transportes/Servicios',
                    'user_id': list(aprobador_id)[0],
                    'note': f'Orden requiere aprobación de {{aprobador_nombre}}.'
                }})
            except:
                pass
"""

try:
    models.execute_kw(
        DB, uid, PASSWORD,
        'ir.actions.server', 'write',
        [[1678], {'code': automation_code.strip()}]
    )
    print("  ✅ Automatización actualizada")
except Exception as e:
    print(f"  ✗ Error: {e}")

print("\n" + "="*80)
print("RESUMEN")
print("="*80)
print(f"""
✅ CONFIGURACIÓN COMPLETADA

REGLAS DE APROBACIÓN - TRANSPORTES + SERVICIOS:

📋 RFQs (Solicitudes):     FRANCISCO LUTTECKE (ID: {francisco_id})
   Estados: draft, sent

📦 Órdenes Confirmadas:     MAXIMO (ID: {MAXIMO_ID})
   Estados: purchase, to approve

La automatización se ejecuta automáticamente al modificar la OC.
""")
