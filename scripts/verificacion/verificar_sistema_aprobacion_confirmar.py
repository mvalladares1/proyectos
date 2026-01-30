#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificar sistema de aprobaciones en botón CONFIRMAR PEDIDO
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
print("VERIFICAR APROBACIONES EN CONFIRMAR PEDIDO")
print("="*80)

# 1. Ver una OC de TRANSPORTES específica
print("\n1. VERIFICANDO OC DE TRANSPORTES:")
print("-" * 80)

oc = models.execute_kw(
    DB, uid, PASSWORD,
    'purchase.order', 'search_read',
    [[['x_studio_categora_de_producto', '=', 'SERVICIOS'], 
      ['state', '=', 'draft']]],
    {'fields': ['id', 'name', 'state'], 'limit': 1}
)

if oc:
    oc_id = oc[0]['id']
    oc_name = oc[0]['name']
    print(f"  OC: {oc_name} (ID: {oc_id})")
    
    # Ver campos de aprobación
    oc_full = models.execute_kw(
        DB, uid, PASSWORD,
        'purchase.order', 'search_read',
        [[['id', '=', oc_id]]],
        {'fields': []}
    )
    
    print(f"\n  Campos relacionados con aprobación:")
    for key, value in sorted(oc_full[0].items()):
        if any(keyword in key.lower() for keyword in ['approv', 'validat', 'confirm', 'state']):
            if value:  # Solo mostrar si tiene valor
                print(f"    {key}: {value}")

# 2. Buscar campos de aprobación en el modelo
print("\n2. CAMPOS DE APROBACIÓN EN PURCHASE.ORDER:")
print("-" * 80)

campos_approval = models.execute_kw(
    DB, uid, PASSWORD,
    'ir.model.fields', 'search_read',
    [[['model', '=', 'purchase.order'],
      '|', '|', 
      ['name', 'ilike', 'approv'],
      ['name', 'ilike', 'validat'],
      ['field_description', 'ilike', 'aprobaci']]],
    {'fields': ['name', 'field_description', 'ttype']}
)

for campo in campos_approval:
    print(f"  {campo['field_description']} ({campo['name']}) - Tipo: {campo['ttype']}")

# 3. Buscar módulo de aprobaciones
print("\n3. BUSCAR REGLAS/TIERS DE APROBACIÓN:")
print("-" * 80)

# Posibles modelos de aprobación
modelos_aprobacion = [
    'purchase.approval.tier',
    'tier.definition',
    'approval.request',
    'tier.review'
]

for modelo in modelos_aprobacion:
    try:
        registros = models.execute_kw(
            DB, uid, PASSWORD,
            modelo, 'search_read',
            [[]],
            {'fields': [], 'limit': 5}
        )
        
        if registros:
            print(f"\n  ✓ Modelo encontrado: {modelo}")
            print(f"    Total registros: {len(registros)}")
            for reg in registros[:3]:
                print(f"    {reg}")
    except:
        pass

# 4. Ver si hay validaciones/reviewers en la OC
print("\n4. VALIDACIONES/REVIEWERS EN LA OC:")
print("-" * 80)

if oc:
    # Buscar tier.review relacionados
    try:
        reviews = models.execute_kw(
            DB, uid, PASSWORD,
            'tier.review', 'search_read',
            [[['res_id', '=', oc_id], ['model', '=', 'purchase.order']]],
            {'fields': ['name', 'status', 'reviewer_id', 'definition_id']}
        )
        
        if reviews:
            print(f"  Tier Reviews encontrados: {len(reviews)}")
            for review in reviews:
                print(f"\n    Review: {review.get('name')}")
                print(f"    Status: {review.get('status')}")
                print(f"    Reviewer: {review.get('reviewer_id')}")
                print(f"    Definition: {review.get('definition_id')}")
    except Exception as e:
        print(f"  No hay tier.review: {str(e)[:80]}")

# 5. Buscar tier.definition (definiciones de aprobación)
print("\n5. TIER DEFINITIONS (Definiciones de aprobación):")
print("-" * 80)

try:
    tier_defs = models.execute_kw(
        DB, uid, PASSWORD,
        'tier.definition', 'search_read',
        [[['model', '=', 'purchase.order']]],
        {'fields': ['name', 'reviewer_id', 'reviewer_group_id', 'python_code', 'active']}
    )
    
    if tier_defs:
        print(f"  Definiciones encontradas: {len(tier_defs)}")
        for tier_def in tier_defs:
            print(f"\n    Nombre: {tier_def.get('name')}")
            print(f"    Activa: {tier_def.get('active')}")
            print(f"    Reviewer: {tier_def.get('reviewer_id')}")
            print(f"    Grupo: {tier_def.get('reviewer_group_id')}")
            if tier_def.get('python_code'):
                print(f"    Código Python:")
                print(f"      {tier_def['python_code'][:200]}")
except Exception as e:
    print(f"  Error: {str(e)[:80]}")

print("\n" + "="*80)
print("CONCLUSIÓN")
print("="*80)
print("""
Necesito identificar el sistema de aprobación que está agregando:
- "Aprobaciones / Finanzas"
- "Compra / Control de Gestión"

Probablemente es un módulo de "Tier Validation" o "Purchase Approval"
que tiene reglas configuradas que se aplican a TODAS las OCs.

Siguiente paso: Modificar las tier.definition para EXCLUIR TRANSPORTES
o configurar tier.definition específicos para TRANSPORTES.
""")
