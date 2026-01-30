#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplicar limpieza de aprobadores a OCs de SERVICIOS existentes
Dejar solo a MAXIMO como aprobador
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
    print("LIMPIAR APROBADORES EN OCS DE SERVICIOS EXISTENTES")
    print("="*80)
    
    # 1. Buscar OCs de SERVICIOS en estado pendiente
    print("\n1. BUSCANDO OCS DE SERVICIOS PENDIENTES:")
    print("-" * 80)
    
    ocs = odoo.search_read(
        'purchase.order',
        [('state', 'in', ['draft', 'sent', 'to approve'])],
        ['id', 'name', 'x_studio_categora_de_producto', 'x_studio_categora', 'state']
    )
    
    ocs_servicios = []
    for oc in ocs:
        es_servicio = False
        
        # Verificar si es de servicios
        if oc.get('x_studio_categora_de_producto') and 'SERVICIO' in str(oc['x_studio_categora_de_producto']).upper():
            es_servicio = True
        elif oc.get('x_studio_categora') and oc['x_studio_categora'] == 'Servicio':
            es_servicio = True
        else:
            # Verificar productos de la OC
            lineas = odoo.search_read(
                'purchase.order.line',
                [('order_id', '=', oc['id'])],
                ['product_id'],
                limit=1
            )
            
            if lineas and lineas[0].get('product_id'):
                producto = odoo.search_read(
                    'product.product',
                    [('id', '=', lineas[0]['product_id'][0])],
                    ['categ_id']
                )
                
                if producto and producto[0].get('categ_id'):
                    categoria = odoo.search_read(
                        'product.category',
                        [('id', '=', producto[0]['categ_id'][0])],
                        ['complete_name']
                    )
                    
                    if categoria and 'SERVICIO' in str(categoria[0].get('complete_name', '')).upper():
                        es_servicio = True
        
        if es_servicio:
            ocs_servicios.append(oc)
    
    print(f"  ✓ OCs de SERVICIOS encontradas: {len(ocs_servicios)}\n")
    for oc in ocs_servicios[:10]:
        print(f"    - {oc['name']} (Estado: {oc['state']})")
    
    if not ocs_servicios:
        print("  ℹ️  No hay OCs de servicios pendientes.")
        return
    
    # 2. Procesar cada OC
    print("\n2. PROCESANDO CADA OC:")
    print("-" * 80)
    
    total_procesadas = 0
    total_actividades_eliminadas = 0
    total_actividades_creadas = 0
    
    for oc in ocs_servicios:
        print(f"\n  OC: {oc['name']} (ID: {oc['id']})")
        
        # Buscar actividades de aprobación
        actividades = odoo.search_read(
            'mail.activity',
            [('res_model', '=', 'purchase.order'),
             ('res_id', '=', oc['id']),
             ('activity_type_id', '=', 9)],  # Grant Approval
            ['id', 'user_id']
        )
        
        if not actividades:
            print(f"    ℹ️  No tiene actividades de aprobación")
            continue
        
        print(f"    Actividades encontradas: {len(actividades)}")
        
        # Identificar actividades a eliminar (todas menos MAXIMO)
        actividades_eliminar = []
        tiene_maximo = False
        
        for act in actividades:
            user_id = act['user_id'][0] if isinstance(act['user_id'], (list, tuple)) else act['user_id']
            user_name = act['user_id'][1] if isinstance(act['user_id'], (list, tuple)) else act['user_id']
            
            if user_id == MAXIMO_ID:
                tiene_maximo = True
                print(f"      ✓ MAXIMO - Mantener")
            else:
                actividades_eliminar.append(act['id'])
                print(f"      ✗ {user_name} - Eliminar")
        
        # Eliminar actividades
        if actividades_eliminar:
            try:
                odoo.models.execute_kw(
                    odoo.db, odoo.uid, odoo.password,
                    'mail.activity', 'unlink',
                    [actividades_eliminar]
                )
                print(f"    ✅ Eliminadas {len(actividades_eliminar)} actividades")
                total_actividades_eliminadas += len(actividades_eliminar)
            except Exception as e:
                print(f"    ✗ Error eliminando: {e}")
                continue
        
        # Crear actividad para MAXIMO si no existe
        if not tiene_maximo:
            try:
                nueva_id = odoo.models.execute_kw(
                    odoo.db, odoo.uid, odoo.password,
                    'mail.activity', 'create',
                    [{
                        'res_model': 'purchase.order',
                        'res_id': oc['id'],
                        'activity_type_id': 9,
                        'summary': 'Aprobación OC Transportes/Servicios',
                        'user_id': MAXIMO_ID,
                        'note': 'Esta orden de compra requiere aprobación de MAXIMO.'
                    }]
                )
                print(f"    ✅ Creada actividad para MAXIMO (ID: {nueva_id})")
                total_actividades_creadas += 1
            except Exception as e:
                print(f"    ✗ Error creando actividad: {e}")
                continue
        
        total_procesadas += 1
    
    # 3. Resumen
    print("\n\n" + "="*80)
    print("RESUMEN")
    print("="*80)
    print(f"  OCs de SERVICIOS encontradas: {len(ocs_servicios)}")
    print(f"  OCs procesadas: {total_procesadas}")
    print(f"  Actividades eliminadas (otros usuarios): {total_actividades_eliminadas}")
    print(f"  Actividades creadas (MAXIMO): {total_actividades_creadas}")
    print(f"\n  ✅ COMPLETADO!")
    print(f"  📋 Ahora Miguel solo verá las aprobaciones asignadas a MAXIMO en Servicios.")

if __name__ == "__main__":
    main()
