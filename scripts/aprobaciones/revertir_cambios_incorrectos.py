#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REVERTIR cambios incorrectos - Solo debe afectar TRANSPORTES, no todos los SERVICIOS
"""
import xmlrpc.client

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

FRANCISCO_ID = 258

print("\n" + "="*80)
print("ANÁLISIS Y REVERSIÓN DE CAMBIOS INCORRECTOS")
print("="*80)

common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

# 1. Buscar campo de Área Solicitante
print("\n1. IDENTIFICANDO CAMPO 'ÁREA SOLICITANTE':")
print("-" * 80)

campos_area = models.execute_kw(
    DB, uid, PASSWORD,
    'ir.model.fields', 'search_read',
    [[['model', '=', 'purchase.order'], 
      '|', ['name', 'ilike', 'area'], ['name', 'ilike', 'solicitante']]],
    {'fields': ['name', 'field_description']}
)

print(f"  Campos encontrados: {len(campos_area)}")
for campo in campos_area:
    print(f"    - {campo['field_description']}: {campo['name']}")

campo_area = None
for c in campos_area:
    if 'solicitante' in c['name'].lower() or 'área' in c['field_description'].lower():
        campo_area = c['name']
        print(f"\n  ✓ Campo identificado: {campo_area}")
        break

if not campo_area:
    campo_area = 'x_studio_area_solicitante'
    print(f"\n  ⚠️  Usando campo por defecto: {campo_area}")

# 2. Verificar OC12384 (área CALIDAD, categoría SERVICIOS)
print("\n2. VERIFICANDO OC12384 (CALIDAD - SERVICIOS):")
print("-" * 80)

oc12384 = models.execute_kw(
    DB, uid, PASSWORD,
    'purchase.order', 'search_read',
    [[['name', '=', 'OC12384']]],
    {'fields': ['id', 'name', campo_area, 'x_studio_categora_de_producto', 'state']}
)

if oc12384:
    area = oc12384[0].get(campo_area)
    print(f"  OC: {oc12384[0]['name']}")
    print(f"  Área: {area}")
    print(f"  Categoría: {oc12384[0].get('x_studio_categora_de_producto')}")
    print(f"  Estado: {oc12384[0]['state']}")
    
    # Ver actividades actuales
    actividades = models.execute_kw(
        DB, uid, PASSWORD,
        'mail.activity', 'search_read',
        [[['res_model', '=', 'purchase.order'], 
          ['res_id', '=', oc12384[0]['id']],
          ['activity_type_id', '=', 9]]],
        {'fields': ['id', 'user_id', 'create_date']}
    )
    
    print(f"\n  Actividades actuales: {len(actividades)}")
    for act in actividades:
        user_name = act['user_id'][1] if isinstance(act['user_id'], (list, tuple)) else ''
        create_date = act.get('create_date', '')
        simbolo = "✓" if act['user_id'][0] == FRANCISCO_ID else "✗"
        print(f"    {simbolo} {user_name} (Creada: {create_date})")

# 3. Buscar TODAS las OCs que modifiqué incorrectamente
print("\n3. BUSCANDO OCs MODIFICADAS INCORRECTAMENTE:")
print("-" * 80)
print("  (SERVICIOS pero NO TRANSPORTES)")

# Buscar OCs con actividades creadas hoy para Francisco
import datetime
hoy = datetime.date.today().strftime('%Y-%m-%d')

# Buscar las actividades que creé hoy para Francisco
actividades_francisco_hoy = models.execute_kw(
    DB, uid, PASSWORD,
    'mail.activity', 'search_read',
    [[['user_id', '=', FRANCISCO_ID],
      ['res_model', '=', 'purchase.order'],
      ['create_date', '>=', hoy]]],
    {'fields': ['id', 'res_id', 'create_date', 'summary']}
)

print(f"\n  Actividades creadas hoy para Francisco: {len(actividades_francisco_hoy)}")

ocs_afectadas = []
for act in actividades_francisco_hoy:
    if 'Transportes/Servicios' in str(act.get('summary', '')):
        ocs_afectadas.append(act['res_id'])

print(f"  OCs potencialmente afectadas: {len(set(ocs_afectadas))}")

# Verificar cuáles NO son TRANSPORTES
ocs_incorrectas = []
for oc_id in set(ocs_afectadas):
    oc = models.execute_kw(
        DB, uid, PASSWORD,
        'purchase.order', 'search_read',
        [[['id', '=', oc_id]]],
        {'fields': ['id', 'name', campo_area, 'x_studio_categora_de_producto']}
    )
    
    if oc:
        area = oc[0].get(campo_area)
        # Si NO es TRANSPORTES, es incorrecta
        if area and 'TRANSPORTE' not in str(area).upper():
            ocs_incorrectas.append(oc[0])
            print(f"\n  ✗ {oc[0]['name']}: Área '{area}' - NO debió modificarse")

# 4. Eliminar actividades de Francisco en OCs incorrectas
print(f"\n4. REVIRTIENDO CAMBIOS EN {len(ocs_incorrectas)} OCs:")
print("-" * 80)

total_revertidas = 0
for oc in ocs_incorrectas:
    print(f"\n  {oc['name']} (Área: {oc.get(campo_area)})")
    
    # Buscar actividad de Francisco creada hoy
    acts_francisco = models.execute_kw(
        DB, uid, PASSWORD,
        'mail.activity', 'search_read',
        [[['res_model', '=', 'purchase.order'],
          ['res_id', '=', oc['id']],
          ['user_id', '=', FRANCISCO_ID],
          ['create_date', '>=', hoy]]],
        {'fields': ['id']}
    )
    
    if acts_francisco:
        try:
            models.execute_kw(
                DB, uid, PASSWORD,
                'mail.activity', 'unlink',
                [[act['id'] for act in acts_francisco]]
            )
            print(f"    ✅ Eliminada actividad de Francisco")
            total_revertidas += 1
        except Exception as e:
            print(f"    ✗ Error: {str(e)[:80]}")

print(f"\n\n  Total OCs revertidas: {total_revertidas}")

# 5. Mostrar solo OCs de TRANSPORTES que SÍ deben tener Francisco
print("\n5. OCs DE TRANSPORTES (CORRECTAS):")
print("-" * 80)

ocs_transportes = []
for oc_id in set(ocs_afectadas):
    oc = models.execute_kw(
        DB, uid, PASSWORD,
        'purchase.order', 'search_read',
        [[['id', '=', oc_id]]],
        {'fields': ['id', 'name', campo_area]}
    )
    
    if oc:
        area = oc[0].get(campo_area)
        if area and 'TRANSPORTE' in str(area).upper():
            ocs_transportes.append(oc[0])
            print(f"  ✓ {oc[0]['name']}: Área '{area}'")

print(f"\n  Total OCs TRANSPORTES correctas: {len(ocs_transportes)}")

print("\n" + "="*80)
print("RESUMEN")
print("="*80)
print(f"""
OCs procesadas incorrectamente: {len(ocs_incorrectas)}
OCs revertidas: {total_revertidas}
OCs TRANSPORTES correctas: {len(ocs_transportes)}

⚠️  Campo de área detectado: {campo_area}

Siguiente paso: Actualizar automatización para usar filtro de ÁREA TRANSPORTES
""")
