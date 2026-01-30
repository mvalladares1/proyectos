#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Identificar qué diferencia una OC de TRANSPORTES vs CALIDAD
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
print("COMPARAR OC12393 (TRANSPORTES) vs OC12384 (CALIDAD)")
print("="*80)

# Buscar todos los campos de purchase.order
campos_po = models.execute_kw(
    DB, uid, PASSWORD,
    'ir.model.fields', 'search_read',
    [[['model', '=', 'purchase.order']]],
    {'fields': ['name', 'field_description'], 'limit': 200}
)

# Obtener OC12393 (TRANSPORTES) completa
print("\n1. OC12393 - TRANSPORTES:")
print("-" * 80)

oc_transportes = models.execute_kw(
    DB, uid, PASSWORD,
    'purchase.order', 'search_read',
    [[['name', '=', 'OC12393']]],
    {'fields': ['id'], 'limit': 1}
)

if oc_transportes:
    oc_t_id = oc_transportes[0]['id']
    
    # Leer TODOS los campos
    oc_t_full = models.execute_kw(
        DB, uid, PASSWORD,
        'purchase.order', 'read',
        [[oc_t_id]]
    )
    
    print(f"  Campos personalizados (x_studio_*):")
    campos_t = {}
    for key, value in sorted(oc_t_full[0].items()):
        if key.startswith('x_studio') and value:
            campos_t[key] = value
            print(f"    {key}: {value}")

# Obtener OC12384 (CALIDAD) completa
print("\n2. OC12384 - CALIDAD:")
print("-" * 80)

oc_calidad = models.execute_kw(
    DB, uid, PASSWORD,
    'purchase.order', 'search_read',
    [[['name', '=', 'OC12384']]],
    {'fields': ['id'], 'limit': 1}
)

if oc_calidad:
    oc_c_id = oc_calidad[0]['id']
    
    # Leer TODOS los campos
    oc_c_full = models.execute_kw(
        DB, uid, PASSWORD,
        'purchase.order', 'read',
        [[oc_c_id]]
    )
    
    print(f"  Campos personalizados (x_studio_*):")
    campos_c = {}
    for key, value in sorted(oc_c_full[0].items()):
        if key.startswith('x_studio') and value:
            campos_c[key] = value
            print(f"    {key}: {value}")

# Comparar diferencias
print("\n3. DIFERENCIAS CLAVE:")
print("-" * 80)

print("\n  Campos SOLO en TRANSPORTES (OC12393):")
for key in campos_t:
    if key not in campos_c or campos_t[key] != campos_c.get(key):
        print(f"    {key}: {campos_t[key]}")

print("\n  Campos SOLO en CALIDAD (OC12384):")
for key in campos_c:
    if key not in campos_t or campos_c[key] != campos_t.get(key):
        print(f"    {key}: {campos_c[key]}")

# Buscar campos con "area", "transportes", "calidad"
print("\n4. CAMPOS RELEVANTES:")
print("-" * 80)

campos_relevantes = [c for c in campos_po if any(keyword in c['field_description'].lower() 
                    for keyword in ['área', 'area', 'transporte', 'calidad', 'departamento'])]

for campo in campos_relevantes:
    val_t = oc_t_full[0].get(campo['name']) if oc_transportes else None
    val_c = oc_c_full[0].get(campo['name']) if oc_calidad else None
    
    if val_t != val_c:
        print(f"\n  {campo['field_description']} ({campo['name']}):")
        print(f"    TRANSPORTES: {val_t}")
        print(f"    CALIDAD: {val_c}")

print("\n" + "="*80)
print("CONCLUSIÓN")
print("="*80)
print("""
Necesito identificar el campo que diferencia TRANSPORTES de CALIDAD.
Probablemente sea:
- Un campo de departamento/área
- El nombre del producto contiene "FLETE" o "TRANSPORTE"
- El proveedor es específico de transportes
""")
