#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crear automatización: SOLO MAXIMO aprueba OCs de TRANSPORTES + SERVICIOS

Esta automatización se ejecutará cuando una OC de categoría SERVICIOS 
sea enviada para aprobación, eliminando todos los aprobadores excepto MAXIMO.
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
    
    MAXIMO_ID = 241
    
    print("\n" + "="*80)
    print("CREAR AUTOMATIZACIÓN: SOLO MAXIMO APRUEBA TRANSPORTES + SERVICIOS")
    print("="*80)
    
    # 1. Verificar si ya existe una automatización similar
    print("\n1. VERIFICANDO AUTOMATIZACIONES EXISTENTES:")
    print("-" * 80)
    
    existing = odoo.search_read(
        'base.automation',
        [('name', 'ilike', 'maximo')],
        ['id', 'name', 'active']
    )
    
    if existing:
        print(f"  ⚠️  Encontradas {len(existing)} automatizaciones con 'MAXIMO':")
        for auto in existing:
            print(f"    - {auto['name']} (ID: {auto['id']}, Activa: {auto['active']})")
        print("\n  Puedes desactivarlas manualmente si es necesario.")
    
    # 2. Obtener ID del modelo purchase.order
    print("\n2. OBTENIENDO ID DEL MODELO PURCHASE.ORDER:")
    print("-" * 80)
    
    model_po = odoo.search_read(
        'ir.model',
        [('model', '=', 'purchase.order')],
        ['id', 'name']
    )
    
    if not model_po:
        print("  ✗ ERROR: No se encontró el modelo purchase.order")
        return
    
    model_po_id = model_po[0]['id']
    print(f"  ✓ Modelo: {model_po[0]['name']} (ID: {model_po_id})")
    
    # 3. Obtener ID del tipo de actividad "Grant Approval"
    print("\n3. OBTENIENDO TIPO DE ACTIVIDAD 'GRANT APPROVAL':")
    print("-" * 80)
    
    activity_type = odoo.search_read(
        'mail.activity.type',
        [('name', '=', 'Grant Approval')],
        ['id', 'name']
    )
    
    activity_type_id = activity_type[0]['id'] if activity_type else 9  # Default 9
    print(f"  ✓ Tipo de actividad ID: {activity_type_id}")
    
    # 4. Crear código Python para la automatización
    automation_code = f"""
# Automatización: SOLO MAXIMO aprueba OCs de TRANSPORTES + SERVICIOS
# ID de MAXIMO: {MAXIMO_ID}

for order in records:
    # Verificar si es una OC de SERVICIOS/TRANSPORTES
    es_servicio = False
    
    # Opción 1: Verificar campo categoría de producto
    if order.x_studio_categora_de_producto and 'SERVICIO' in order.x_studio_categora_de_producto.upper():
        es_servicio = True
    
    # Opción 2: Verificar campo categoría
    if order.x_studio_categora and order.x_studio_categora == 'Servicio':
        es_servicio = True
    
    # Opción 3: Verificar productos de la línea
    for line in order.order_line:
        if line.product_id and line.product_id.categ_id:
            if 'SERVICIO' in line.product_id.categ_id.display_name.upper():
                es_servicio = True
                break
    
    if es_servicio:
        # Buscar todas las actividades de aprobación actuales
        activities = env['mail.activity'].search([
            ('res_model', '=', 'purchase.order'),
            ('res_id', '=', order.id),
            ('activity_type_id.name', '=', 'Grant Approval')
        ])
        
        # Eliminar todas las actividades que NO sean de MAXIMO
        activities_to_remove = activities.filtered(lambda a: a.user_id.id != {MAXIMO_ID})
        if activities_to_remove:
            activities_to_remove.unlink()
        
        # Verificar si ya existe actividad para MAXIMO
        maximo_activity = activities.filtered(lambda a: a.user_id.id == {MAXIMO_ID})
        
        # Si no existe, crearla
        if not maximo_activity and order.state in ['sent', 'to approve']:
            env['mail.activity'].create({{
                'res_model': 'purchase.order',
                'res_id': order.id,
                'activity_type_id': {activity_type_id},
                'summary': 'Aprobación OC Transportes/Servicios',
                'user_id': {MAXIMO_ID},
                'note': 'Esta orden de compra requiere aprobación de MAXIMO.'
            }})
"""
    
    print("\n4. CÓDIGO DE LA AUTOMATIZACIÓN:")
    print("-" * 80)
    print(automation_code)
    
    # 5. Crear la acción de servidor
    print("\n5. CREANDO ACCIÓN DE SERVIDOR:")
    print("-" * 80)
    
    try:
        action_id = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'ir.actions.server', 'create',
            [{
                'name': 'Asignar solo MAXIMO - Servicios',
                'model_id': model_po_id,
                'state': 'code',
                'code': automation_code.strip()
            }]
        )
        print(f"  ✓ Acción creada con ID: {action_id}")
    except Exception as e:
        print(f"  ✗ ERROR creando acción: {e}")
        return
    
    # 6. Crear la automatización
    print("\n6. CREANDO AUTOMATIZACIÓN:")
    print("-" * 80)
    
    try:
        automation_id = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'base.automation', 'create',
            [{
                'name': 'Aprobación MAXIMO - Transportes + Servicios',
                'model_id': model_po_id,
                'trigger': 'on_write',
                'active': True,
                'action_server_id': action_id,
                'filter_domain': "[('state', 'in', ['sent', 'to approve'])]",
                'filter_pre_domain': "[]"
            }]
        )
        
        print(f"  ✓ Automatización creada con ID: {automation_id}")
        print(f"\n  ✅ SUCCESS! La automatización está activa.")
        print(f"  📋 Ahora, cada vez que se modifique una OC en estado 'sent' o 'to approve',")
        print(f"     si es de SERVICIOS/TRANSPORTES, solo MAXIMO ({MAXIMO_ID}) será el aprobador.")
        
    except Exception as e:
        print(f"  ✗ ERROR creando automatización: {e}")
        
        # Limpiar la acción creada
        try:
            odoo.models.execute_kw(
                odoo.db, odoo.uid, odoo.password,
                'ir.actions.server', 'unlink',
                [[action_id]]
            )
            print(f"  🧹 Acción {action_id} eliminada por seguridad")
        except:
            pass
        
        return
    
    # 7. Probar con OC12312
    print("\n7. PROBANDO CON OC12312:")
    print("-" * 80)
    print("  Para activar la automatización, necesitas modificar la OC.")
    print("  Puedes hacerlo desde Odoo o ejecutar:")
    print(f"  odoo.write('purchase.order', oc_id, {{'note': 'Trigger automation'}})")

if __name__ == "__main__":
    main()
