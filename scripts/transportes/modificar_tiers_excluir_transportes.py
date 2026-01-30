#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Buscar y modificar tier.definition para TRANSPORTES
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
print("BUSCAR TIER DEFINITIONS EN PURCHASE.ORDER")
print("="*80)

# 1. Buscar tier.definition
print("\n1. TIER DEFINITIONS ACTIVAS:")
print("-" * 80)

try:
    tier_defs = models.execute_kw(
        DB, uid, PASSWORD,
        'tier.definition', 'search_read',
        [[['model', '=', 'purchase.order'], ['active', '=', True]]],
        {'fields': ['id', 'name', 'sequence', 'python_code', 'reviewer_id', 'reviewer_group_id']}
    )
    
    print(f"  Tier Definitions encontradas: {len(tier_defs)}\n")
    
    for tier in tier_defs:
        print(f"  ID: {tier['id']}")
        print(f"  Nombre: {tier['name']}")
        print(f"  Secuencia: {tier.get('sequence')}")
        
        if tier.get('reviewer_id'):
            print(f"  Reviewer (usuario): {tier['reviewer_id']}")
        
        if tier.get('reviewer_group_id'):
            grupo = tier['reviewer_group_id']
            grupo_name = grupo[1] if isinstance(grupo, (list, tuple)) else grupo
            print(f"  Reviewer (grupo): {grupo_name}")
        
        if tier.get('python_code'):
            print(f"  Código Python:")
            lines = tier['python_code'].split('\n')
            for line in lines[:10]:
                print(f"    {line}")
            if len(lines) > 10:
                print(f"    ... ({len(lines) - 10} líneas más)")
        
        print()
    
    # 2. Identificar cuáles deben excluir TRANSPORTES
    print("\n2. ANÁLISIS - TIERS QUE DEBEN EXCLUIR TRANSPORTES:")
    print("-" * 80)
    
    for tier in tier_defs:
        debe_modificar = False
        razon = ""
        
        # Si el código no menciona TRANSPORTES ni FLETE, debe excluirlos
        codigo = tier.get('python_code', '').upper()
        if 'TRANSPORTE' not in codigo and 'FLETE' not in codigo:
            debe_modificar = True
            razon = "No tiene filtro de TRANSPORTES"
        
        if debe_modificar:
            print(f"\n  ✗ Tier {tier['id']}: {tier['name']}")
            print(f"    Razón: {razon}")
            print(f"    Acción: Agregar exclusión de TRANSPORTES")
            
            # Proponer código modificado
            codigo_actual = tier.get('python_code', 'result = True')
            
            codigo_nuevo = f"""# Excluir TRANSPORTES (tienen flujo especial)
es_transporte = False

# Verificar producto con FLETE
for line in rec.order_line:
    if line.product_id and 'FLETE' in line.product_id.name.upper():
        es_transporte = True
        break

# Verificar proveedor TRANSPORTE
if rec.partner_id and ('TRANSPORTE' in rec.partner_id.name.upper() or 'ARRAYANES' in rec.partner_id.name.upper()):
    es_transporte = True

# Si es TRANSPORTES, no aplicar este tier
if es_transporte:
    result = False
else:
    # Código original
    {codigo_actual}
"""
            
            print(f"\n    Código propuesto:")
            for line in codigo_nuevo.split('\n')[:15]:
                print(f"      {line}")
    
    # 3. Desactivar o modificar tiers
    print("\n\n3. ¿DESACTIVAR O MODIFICAR TIERS?")
    print("-" * 80)
    print("""
    Opciones:
    
    A) DESACTIVAR tiers existentes solo para TRANSPORTES
       → Modificar python_code para excluir TRANSPORTES
    
    B) CREAR tier.definition específico para TRANSPORTES
       → Nuevo tier con Francisco + Maximo (draft/sent)
       → Nuevo tier con Felipe Horst (purchase)
    
    Recomendación: Opción A (modificar código)
    """)
    
    # 4. Aplicar modificaciones
    print("\n4. APLICANDO MODIFICACIONES:")
    print("-" * 80)
    
    modificados = 0
    for tier in tier_defs:
        codigo = tier.get('python_code', '').upper()
        if 'TRANSPORTE' not in codigo and 'FLETE' not in codigo:
            codigo_actual = tier.get('python_code', 'result = True')
            
            codigo_nuevo = f"""# Excluir TRANSPORTES (tienen flujo especial con Francisco + Maximo + Felipe)
es_transporte = False
for line in rec.order_line:
    if line.product_id and 'FLETE' in line.product_id.name.upper():
        es_transporte = True
        break
if rec.partner_id and ('TRANSPORTE' in rec.partner_id.name.upper() or 'ARRAYANES' in rec.partner_id.name.upper()):
    es_transporte = True

if es_transporte:
    result = False
else:
    {codigo_actual}
"""
            
            try:
                models.execute_kw(
                    DB, uid, PASSWORD,
                    'tier.definition', 'write',
                    [[tier['id']], {'python_code': codigo_nuevo}]
                )
                print(f"  ✅ Tier {tier['id']} ({tier['name']}): Modificado")
                modificados += 1
            except Exception as e:
                print(f"  ✗ Tier {tier['id']}: Error - {str(e)[:60]}")
    
    print(f"\n  Total modificados: {modificados}")
    
except Exception as e:
    print(f"  Error: {e}")

print("\n" + "="*80)
print("RESUMEN")
print("="*80)
print(f"""
✅ Tiers modificados para EXCLUIR TRANSPORTES

Ahora las OCs de TRANSPORTES:
- NO pasarán por "Aprobaciones / Finanzas"
- NO pasarán por "Compra / Control de Gestión"
- SOLO usarán las actividades: Francisco + Maximo (draft/sent) → Felipe Horst (purchase)

El botón CONFIRMAR PEDIDO ya no mostrará aprobadores extra para TRANSPORTES.
""")
