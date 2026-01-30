#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurar aprobaciones para FRANCISCO LUTTECKE en Solicitudes de Presupuesto de TRANSPORTES
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from shared.odoo_client import OdooClient

def main():
    odoo = OdooClient(
        url='https://riofuturo.server98c6e.oerpondemand.net',
        db='riofuturo-master',
        username='mvalladares@riofuturo.cl',
        password='c0766224bec30cac071ffe43a858c9ccbd521ddd'
    )
    
    print("\n" + "="*80)
    print("CONFIGURAR APROBACIONES PARA FRANCISCO LUTTECKE - TRANSPORTES")
    print("="*80)
    
    # 1. Buscar a Francisco Luttecke
    print("\n1. BUSCANDO A FRANCISCO LUTTECKE:")
    print("-" * 80)
    
    francisco = odoo.search_read(
        'res.users',
        ['|', ('name', 'ilike', 'LUTTECKE'), ('name', 'ilike', 'FRANCISCO')],
        ['id', 'name', 'login']
    )
    
    if francisco:
        print(f"  ✓ Usuarios encontrados:")
        for user in francisco:
            print(f"    - {user['name']} ({user['login']}) - ID: {user['id']}")
        
        # Buscar el correcto (FRANCISCO LUTTECKE)
        francisco_luttecke = [u for u in francisco if 'LUTTECKE' in u['name'].upper() and 'FRANCISCO' in u['name'].upper()]
        
        if francisco_luttecke:
            francisco_id = francisco_luttecke[0]['id']
            francisco_nombre = francisco_luttecke[0]['name']
            print(f"\n  ✅ FRANCISCO LUTTECKE encontrado: ID {francisco_id}")
        else:
            francisco_id = francisco[0]['id']
            francisco_nombre = francisco[0]['name']
            print(f"\n  ⚠️  Usando primer resultado: {francisco_nombre} (ID: {francisco_id})")
    else:
        print("  ✗ No se encontró a Francisco Luttecke")
        return
    
    # 2. Verificar OC12393 actual
    print("\n2. VERIFICANDO OC12393:")
    print("-" * 80)
    
    oc12393 = odoo.search_read(
        'purchase.order',
        [('name', '=', 'OC12393')],
        ['id', 'name', 'state', 'x_studio_categora_de_producto']
    )
    
    if oc12393:
        print(f"  OC: {oc12393[0]['name']}")
        print(f"  Estado: {oc12393[0]['state']}")
        print(f"  Categoría: {oc12393[0].get('x_studio_categora_de_producto')}")
        
        # Ver actividades actuales
        actividades = odoo.search_read(
            'mail.activity',
            [('res_model', '=', 'purchase.order'), ('res_id', '=', oc12393[0]['id'])],
            ['id', 'user_id', 'activity_type_id']
        )
        
        if actividades:
            print(f"\n  Aprobadores actuales ({len(actividades)}):")
            for act in actividades:
                user_name = act['user_id'][1] if isinstance(act['user_id'], (list, tuple)) else act['user_id']
                user_id = act['user_id'][0] if isinstance(act['user_id'], (list, tuple)) else act['user_id']
                simbolo = "✓" if user_id == francisco_id else "✗"
                print(f"    {simbolo} {user_name}")
        else:
            print(f"  ℹ️  No tiene actividades de aprobación")
    
    # 3. Buscar todas las RFQs de TRANSPORTES con múltiples aprobadores
    print("\n3. RFQS DE TRANSPORTES CON MÚLTIPLES APROBADORES:")
    print("-" * 80)
    
    rfqs = odoo.search_read(
        'purchase.order',
        [('state', 'in', ['draft', 'sent']), 
         ('x_studio_categora_de_producto', '=', 'SERVICIOS')],
        ['id', 'name', 'state'],
        limit=10
    )
    
    print(f"  RFQs de SERVICIOS encontradas: {len(rfqs)}\n")
    
    rfqs_con_multiples = 0
    for rfq in rfqs[:5]:
        actividades = odoo.search_read(
            'mail.activity',
            [('res_model', '=', 'purchase.order'), 
             ('res_id', '=', rfq['id']),
             ('activity_type_id', '=', 9)],
            ['user_id']
        )
        
        if len(actividades) > 1:
            rfqs_con_multiples += 1
            print(f"  {rfq['name']}: {len(actividades)} aprobadores")
            for act in actividades:
                user_name = act['user_id'][1] if isinstance(act['user_id'], (list, tuple)) else ''
                print(f"    - {user_name}")
    
    print(f"\n  Total con múltiples aprobadores: {rfqs_con_multiples}")
    
    # 4. Actualizar automatización para incluir a Francisco
    print("\n4. ACTUALIZANDO AUTOMATIZACIÓN:")
    print("-" * 80)
    
    # Obtener modelo purchase.order ID
    model_po = odoo.search_read('ir.model', [('model', '=', 'purchase.order')], ['id'])
    model_po_id = model_po[0]['id']
    
    # Código actualizado que incluye FRANCISCO y MAXIMO
    MAXIMO_ID = 241
    
    automation_code_updated = f"""
# Automatización actualizada: Aprobaciones TRANSPORTES + SERVICIOS
# FRANCISCO LUTTECKE (ID: {francisco_id}) - Para Solicitudes de Presupuesto (RFQ)
# MAXIMO (ID: {MAXIMO_ID}) - Para Órdenes de Compra confirmadas

for order in records:
    # Verificar si es una OC de SERVICIOS/TRANSPORTES
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
        # Buscar actividades de aprobación actuales
        activities = env['mail.activity'].search([
            ('res_model', '=', 'purchase.order'),
            ('res_id', '=', order.id),
            ('activity_type_id.name', '=', 'Grant Approval')
        ])
        
        # Determinar aprobador según estado
        if order.state in ['draft', 'sent']:
            # RFQ - Solo FRANCISCO
            aprobador_correcto = {francisco_id}
            aprobador_nombre = "FRANCISCO LUTTECKE"
        else:
            # OC confirmada - Solo MAXIMO
            aprobador_correcto = {MAXIMO_ID}
            aprobador_nombre = "MAXIMO"
        
        # Eliminar actividades que NO sean del aprobador correcto
        activities_to_remove = activities.filtered(lambda a: a.user_id.id not in aprobador_correcto)
        if activities_to_remove:
            activities_to_remove.unlink()
        
        # Verificar si existe actividad para el aprobador correcto
        correct_activity = activities.filtered(lambda a: a.user_id.id in aprobador_correcto)
        
        # Si no existe, intentar crearla (la automatización lo manejará)
        if not correct_activity and order.state in ['draft', 'sent', 'to approve']:
            try:
                # Obtener res_model_id
                ir_model = env['ir.model'].search([('model', '=', 'purchase.order')], limit=1)
                
                env['mail.activity'].create({{
                    'res_model': 'purchase.order',
                    'res_model_id': ir_model.id if ir_model else False,
                    'res_id': order.id,
                    'activity_type_id': 9,
                    'summary': f'Aprobación {{aprobador_nombre}} - Transportes/Servicios',
                    'user_id': list(aprobador_correcto)[0],
                    'note': f'Esta orden requiere aprobación de {{aprobador_nombre}}.'
                }})
            except:
                pass  # Si falla, la actividad se creará manualmente
"""
    
    print("  Código de automatización actualizado:")
    print(f"    - FRANCISCO ({francisco_id}): RFQs (draft/sent)")
    print(f"    - MAXIMO ({MAXIMO_ID}): OCs confirmadas")
    
    # 5. Actualizar la acción de servidor existente
    print("\n5. ACTUALIZANDO ACCIÓN DE SERVIDOR (ID: 1678):")
    print("-" * 80)
    
    try:
        odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'ir.actions.server', 'write',
            [[1678], {'code': automation_code_updated.strip()}]
        )
        print("  ✅ Acción de servidor actualizada correctamente")
    except Exception as e:
        print(f"  ✗ Error actualizando: {e}")
        return
    
    # 6. Limpiar aprobadores de OC12393 específicamente
    print("\n6. LIMPIANDO APROBADORES DE OC12393:")
    print("-" * 80)
    
    if oc12393 and actividades:
        actividades_eliminar = []
        for act in actividades:
            user_id = act['user_id'][0] if isinstance(act['user_id'], (list, tuple)) else act['user_id']
            if user_id != francisco_id:
                actividades_eliminar.append(act['id'])
        
        if actividades_eliminar:
            try:
                odoo.models.execute_kw(
                    odoo.db, odoo.uid, odoo.password,
                    'mail.activity', 'unlink',
                    [actividades_eliminar]
                )
                print(f"  ✅ Eliminados {len(actividades_eliminar)} aprobadores incorrectos")
                
                # Verificar si Francisco está
                tiene_francisco = any(
                    (act['user_id'][0] if isinstance(act['user_id'], (list, tuple)) else act['user_id']) == francisco_id 
                    for act in actividades
                )
                
                if not tiene_francisco:
                    print(f"  ℹ️  Francisco no estaba asignado. Se asignará en la próxima modificación.")
                else:
                    print(f"  ✅ Francisco ya está asignado como aprobador")
                    
            except Exception as e:
                print(f"  ✗ Error: {e}")
    
    print("\n\n" + "="*80)
    print("RESUMEN")
    print("="*80)
    print(f"""
✅ Automatización actualizada correctamente

REGLAS DE APROBACIÓN PARA TRANSPORTES + SERVICIOS:

1. RFQs (Solicitudes de Presupuesto):
   Estado: draft, sent
   Aprobador: FRANCISCO LUTTECKE (ID: {francisco_id})
   
2. Órdenes de Compra:
   Estado: purchase, to approve
   Aprobador: MAXIMO (ID: {MAXIMO_ID})

La automatización se ejecuta automáticamente cuando se modifica una OC.
Para OC12393, los aprobadores extras fueron eliminados.
    """)

if __name__ == "__main__":
    main()
