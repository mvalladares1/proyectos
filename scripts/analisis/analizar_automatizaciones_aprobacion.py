#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analizar configuración de aprobaciones automáticas en OCs
Objetivo: Identificar por qué se asignan múltiples aprobadores a Transportes + Servicios
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
    
    maximo_id = 241  # ID de MÁXIMO
    
    print("\n" + "="*80)
    print("ANÁLISIS DE AUTOMATIZACIONES Y REGLAS DE APROBACIÓN")
    print("="*80)
    
    # 1. Analizar las automatizaciones Check 1 y Check 2
    print("\n1. AUTOMATIZACIONES EN PURCHASE.ORDER:")
    print("-" * 80)
    
    automations = odoo.search_read(
        'base.automation',
        [('model_id.model', '=', 'purchase.order')],
        ['name', 'trigger', 'filter_domain', 'filter_pre_domain', 
         'code', 'state', 'active']
    )
    
    for auto in automations:
        print(f"\n  Automatización: {auto['name']}")
        print(f"  ID: {auto['id']}")
        print(f"  Trigger: {auto.get('trigger')}")
        print(f"  Estado: {'Activa' if auto.get('active') else 'Inactiva'}")
        print(f"  State: {auto.get('state')}")
        
        if auto.get('filter_domain'):
            print(f"  Dominio filtro: {auto['filter_domain']}")
        if auto.get('filter_pre_domain'):
            print(f"  Pre-dominio: {auto['filter_pre_domain']}")
        
        if auto.get('code'):
            print(f"  Código Python:")
            print("  " + "-" * 76)
            code_lines = auto['code'].split('\n')
            for line in code_lines[:30]:  # Primeras 30 líneas
                print(f"  {line}")
            if len(code_lines) > 30:
                print(f"  ... ({len(code_lines) - 30} líneas más)")
    
    # 2. Buscar campos personalizados en purchase.order relacionados con aprobación
    print("\n\n2. CAMPOS PERSONALIZADOS EN PURCHASE.ORDER (aprobación):")
    print("-" * 80)
    
    campos = odoo.search_read(
        'ir.model.fields',
        [('model', '=', 'purchase.order'), 
         '|', ('name', 'ilike', 'aprov'), ('name', 'ilike', 'approval')],
        ['name', 'field_description', 'ttype']
    )
    
    if campos:
        for campo in campos:
            print(f"  - {campo['field_description']} ({campo['name']}) - Tipo: {campo['ttype']}")
    else:
        print("  No se encontraron campos personalizados")
    
    # 3. Buscar campos relacionados con categoría o tipo
    print("\n\n3. CAMPOS DE CATEGORÍA/TIPO EN PURCHASE.ORDER:")
    print("-" * 80)
    
    campos_cat = odoo.search_read(
        'ir.model.fields',
        [('model', '=', 'purchase.order'),
         '|', '|', ('name', 'ilike', 'categor'), 
         ('name', 'ilike', 'tipo'), ('name', 'ilike', 'type')],
        ['name', 'field_description', 'ttype']
    )
    
    if campos_cat:
        for campo in campos_cat:
            print(f"  - {campo['field_description']} ({campo['name']}) - Tipo: {campo['ttype']}")
    
    # 4. Examinar una OC específica de Servicios para ver qué campos tiene
    print("\n\n4. EXAMINAR OC12312 (SERVICIOS) - VALORES DE CAMPOS:")
    print("-" * 80)
    
    oc = odoo.search_read(
        'purchase.order',
        [('name', '=', 'OC12312')],
        []  # Todos los campos
    )
    
    if oc:
        oc_data = oc[0]
        # Buscar campos x_studio o personalizados
        print("\n  Campos personalizados (x_studio_*):")
        for key, value in sorted(oc_data.items()):
            if key.startswith('x_studio'):
                print(f"    {key}: {value}")
        
        print("\n  Campos relevantes:")
        campos_relevantes = ['order_line', 'user_id', 'partner_id', 'state', 
                            'amount_total', 'picking_type_id', 'company_id']
        for campo in campos_relevantes:
            if campo in oc_data:
                print(f"    {campo}: {oc_data[campo]}")
    
    # 5. Buscar si hay reglas de flujo de trabajo (workflow rules)
    print("\n\n5. BUSCANDO REGLAS DE FLUJO DE TRABAJO:")
    print("-" * 80)
    
    try:
        workflow_rules = odoo.search_read(
            'workflow.rule',
            [],
            limit=10
        )
        if workflow_rules:
            print(f"  Encontradas {len(workflow_rules)} reglas de workflow")
            for rule in workflow_rules:
                print(f"  - {rule}")
    except Exception as e:
        print(f"  No existe modelo workflow.rule: {str(e)[:100]}")
    
    # 6. Buscar acciones de servidor relacionadas
    print("\n\n6. ACCIONES DE SERVIDOR (Check 1 y Check 2):")
    print("-" * 80)
    
    server_actions = odoo.search_read(
        'ir.actions.server',
        ['|', ('name', 'ilike', 'check'), ('id', 'in', [1015, 1016])],
        ['name', 'model_id', 'state', 'code', 'crud_model_id']
    )
    
    for action in server_actions:
        print(f"\n  Acción: {action['name']} (ID: {action['id']})")
        print(f"  Modelo: {action.get('model_id')}")
        print(f"  Estado: {action.get('state')}")
        
        if action.get('code'):
            print(f"  Código:")
            print("  " + "-" * 76)
            code_lines = action['code'].split('\n')
            for line in code_lines[:40]:
                print(f"  {line}")
            if len(code_lines) > 40:
                print(f"  ... ({len(code_lines) - 40} líneas más)")
    
    # 7. Buscar si hay tablas de configuración de aprobadores por categoría
    print("\n\n7. BUSCANDO TABLAS DE CONFIGURACIÓN DE APROBADORES:")
    print("-" * 80)
    
    modelos_posibles = [
        'purchase.approval.config',
        'purchase.approval.rule',
        'purchase.approver',
        'purchase.approval.category',
        'x_purchase_approval'
    ]
    
    for modelo in modelos_posibles:
        try:
            registros = odoo.search_read(modelo, [], limit=5)
            if registros:
                print(f"\n  ✓ Modelo encontrado: {modelo}")
                print(f"    Registros: {len(registros)}")
                for reg in registros[:2]:
                    print(f"    {reg}")
        except:
            pass

if __name__ == "__main__":
    main()
