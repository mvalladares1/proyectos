#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificar configuración de aprobaciones por área
Objetivo: Las OC de "Transportes + Servicios" deben ir SOLO a MAXIMO
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from shared.odoo_client import OdooClient

def main():
    # Usar credenciales directas con URL correcta
    odoo = OdooClient(
        url='https://riofuturo.server98c6e.oerpondemand.net',
        db='riofuturo-master',
        username='mvalladares@riofuturo.cl',
        password='c0766224bec30cac071ffe43a858c9ccbd521ddd'
    )
    
    print("\n" + "="*80)
    print("ANÁLISIS DE APROBACIONES POR ÁREA - TRANSPORTES + SERVICIOS")
    print("="*80)
    
    # 1. Buscar al usuario MAXIMO
    print("\n1. BUSCANDO USUARIO MAXIMO:")
    print("-" * 80)
    
    usuarios_maximo = odoo.search_read(
        'res.users',
        ['|', ('name', 'ilike', 'maximo'), ('login', 'ilike', 'maximo')],
        ['name', 'login', 'id']
    )
    
    if usuarios_maximo:
        for user in usuarios_maximo:
            print(f"  ✓ Encontrado: {user['name']} ({user['login']}) - ID: {user['id']}")
        maximo_id = usuarios_maximo[0]['id']
    else:
        print("  ✗ No se encontró usuario MAXIMO")
        return
    
    # 2. Buscar categorías relacionadas con Transportes/Servicios
    print("\n2. BUSCANDO CATEGORÍAS DE PRODUCTO (Transportes/Servicios):")
    print("-" * 80)
    
    categorias = odoo.search_read(
        'product.category',
        ['|', ('name', 'ilike', 'transporte'), ('name', 'ilike', 'servicio')],
        ['name', 'id', 'complete_name']
    )
    
    if categorias:
        print(f"  Categorías encontradas: {len(categorias)}\n")
        for cat in categorias:
            print(f"  - {cat.get('complete_name') or cat['name']} (ID: {cat['id']})")
    else:
        print("  ✗ No se encontraron categorías")
    
    # 3. Buscar OCs recientes del área Transportes/Servicios
    print("\n3. ÓRDENES DE COMPRA RECIENTES (Transportes/Servicios):")
    print("-" * 80)
    
    # Buscar OCs con productos de esas categorías
    ocs = odoo.search_read(
        'purchase.order',
        [('state', 'in', ['draft', 'sent', 'to approve'])],
        ['name', 'partner_id', 'state', 'amount_total', 'create_date'],
        limit=20
    )
    
    print(f"  OCs en estado borrador/enviado/por aprobar: {len(ocs)}\n")
    
    ocs_servicios = []
    for oc in ocs:
        # Verificar si tiene líneas con productos de servicios/transportes
        lineas = odoo.search_read(
            'purchase.order.line',
            [('order_id', '=', oc['id'])],
            ['product_id']
        )
        
        for linea in lineas:
            if linea.get('product_id'):
                producto = odoo.search_read(
                    'product.product',
                    [('id', '=', linea['product_id'][0])],
                    ['categ_id', 'name']
                )
                
                if producto and producto[0].get('categ_id'):
                    cat_id = producto[0]['categ_id'][0]
                    categoria = odoo.search_read(
                        'product.category',
                        [('id', '=', cat_id)],
                        ['complete_name', 'name']
                    )
                    
                    if categoria:
                        cat_name = categoria[0].get('complete_name') or categoria[0]['name']
                        if 'SERVICIO' in cat_name.upper() or 'TRANSPORTE' in cat_name.upper():
                            ocs_servicios.append({
                                'oc': oc,
                                'categoria': cat_name,
                                'producto': producto[0]['name']
                            })
                            break
    
    if ocs_servicios:
        print(f"  OCs de Transportes/Servicios encontradas: {len(ocs_servicios)}\n")
        for item in ocs_servicios[:5]:
            print(f"  - OC: {item['oc']['name']}")
            print(f"    Estado: {item['oc']['state']}")
            print(f"    Categoría: {item['categoria']}")
            print(f"    Producto: {item['producto']}")
            print()
    
    # 4. Verificar actividades asignadas a estas OCs
    print("\n4. ACTIVIDADES DE APROBACIÓN EN ESTAS OCS:")
    print("-" * 80)
    
    for item in ocs_servicios[:5]:
        oc_id = item['oc']['id']
        actividades = odoo.search_read(
            'mail.activity',
            [('res_model', '=', 'purchase.order'), ('res_id', '=', oc_id)],
            ['summary', 'user_id', 'activity_type_id', 'date_deadline']
        )
        
        if actividades:
            print(f"\n  OC: {item['oc']['name']}")
            for act in actividades:
                user_asignado = act.get('user_id')
                if user_asignado:
                    user_name = user_asignado[1] if isinstance(user_asignado, (list, tuple)) else user_asignado
                    user_id = user_asignado[0] if isinstance(user_asignado, (list, tuple)) else user_asignado
                    
                    es_maximo = user_id == maximo_id
                    simbolo = "✓" if es_maximo else "✗"
                    
                    print(f"    {simbolo} Asignado a: {user_name} (ID: {user_id})")
                    print(f"      Tipo: {act.get('activity_type_id')}")
                    print(f"      Resumen: {act.get('summary')}")
    
    # 5. Verificar si existen reglas de aprobación
    print("\n5. BUSCANDO REGLAS/CONFIGURACIÓN DE APROBACIONES:")
    print("-" * 80)
    
    # Buscar en diferentes modelos posibles
    modelos_posibles = [
        'purchase.approval.rule',
        'purchase.approval.config',
        'approval.category',
        'approval.approver'
    ]
    
    for modelo in modelos_posibles:
        try:
            reglas = odoo.search_read(modelo, [], limit=10)
            if reglas:
                print(f"\n  ✓ Encontrado modelo: {modelo}")
                print(f"    Registros: {len(reglas)}")
                for regla in reglas[:3]:
                    print(f"    - {regla}")
        except Exception as e:
            if 'does not exist' not in str(e):
                print(f"  ℹ️  Error en {modelo}: {str(e)[:100]}")
    
    # 6. Buscar automatizaciones que asignen actividades
    print("\n6. AUTOMATIZACIONES QUE CREAN ACTIVIDADES:")
    print("-" * 80)
    
    try:
        automatizaciones = odoo.search_read(
            'base.automation',
            [('model_id.model', '=', 'purchase.order')],
            ['name', 'trigger', 'action_server_id']
        )
        
        if automatizaciones:
            print(f"  Automatizaciones en purchase.order: {len(automatizaciones)}\n")
            for auto in automatizaciones:
                print(f"  - {auto['name']}")
                print(f"    Trigger: {auto.get('trigger')}")
                if auto.get('action_server_id'):
                    print(f"    Acción: {auto['action_server_id']}")
                print()
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == "__main__":
    main()
