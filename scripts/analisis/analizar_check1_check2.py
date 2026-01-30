#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analizar automatizaciones Check 1 y Check 2 que crean aprobadores
"""
import xmlrpc.client

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

print("\n" + "="*80)
print("ANALIZAR AUTOMATIZACIONES QUE CREAN APROBADORES")
print("="*80)

# 1. Ver automatizaciones Check 1 y Check 2
print("\n1. AUTOMATIZACIONES Check 1 y Check 2:")
print("-" * 80)

autos = models.execute_kw(
    DB, uid, PASSWORD,
    'base.automation', 'search_read',
    [[['id', 'in', [1, 2]]]],
    {'fields': ['id', 'name', 'filter_domain', 'action_server_id']}
)

for auto in autos:
    print(f"\nAutomatización: {auto['name']} (ID: {auto['id']})")
    print(f"Dominio: {auto.get('filter_domain')}")
    
    if auto.get('action_server_id'):
        action_id = auto['action_server_id'][0] if isinstance(auto['action_server_id'], (list, tuple)) else auto['action_server_id']
        
        # Ver código de la acción
        action = models.execute_kw(
            DB, uid, PASSWORD,
            'ir.actions.server', 'search_read',
            [[['id', '=', action_id]]],
            {'fields': ['name', 'code', 'child_ids']}
        )
        
        if action and action[0].get('code'):
            print(f"\nCódigo:")
            code_lines = action[0]['code'].split('\n')
            for line in code_lines:
                if line.strip():
                    print(f"  {line}")
        
        # Ver acciones hijas
        if action and action[0].get('child_ids'):
            print(f"\nAcciones hijas: {action[0]['child_ids']}")
            
            child_actions = models.execute_kw(
                DB, uid, PASSWORD,
                'ir.actions.server', 'search_read',
                [[['id', 'in', action[0]['child_ids']]]],
                {'fields': ['name', 'code']}
            )
            
            for child in child_actions:
                print(f"\n  Acción hija: {child['name']}")
                if child.get('code'):
                    child_lines = child['code'].split('\n')
                    for line in child_lines[:20]:
                        if line.strip():
                            print(f"    {line}")

# 2. Buscar todas las automatizaciones activas en purchase.order
print("\n\n2. TODAS LAS AUTOMATIZACIONES ACTIVAS EN PURCHASE.ORDER:")
print("-" * 80)

all_autos = models.execute_kw(
    DB, uid, PASSWORD,
    'base.automation', 'search_read',
    [[['model_id.model', '=', 'purchase.order'], ['active', '=', True]]],
    {'fields': ['id', 'name', 'trigger', 'filter_domain']}
)

print(f"Total: {len(all_autos)}\n")
for auto in all_autos:
    print(f"  {auto['id']}: {auto['name']}")
    print(f"    Trigger: {auto.get('trigger')}")
    print(f"    Dominio: {auto.get('filter_domain')}")
    print()

print("\n" + "="*80)
print("CONCLUSIÓN")
print("="*80)
print("""
Las automatizaciones Check 1 y Check 2 probablemente están creando
los aprobadores "Aprobaciones / Finanzas" y "Compra / Control de Gestión"
según el tipo de producto (MP o Insumos).

Necesito modificar esas automatizaciones para que NO se ejecuten en TRANSPORTES.
""")
