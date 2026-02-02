"""
Buscar quality checks con defectos reales (valores > 0)
"""
import xmlrpc.client
from datetime import datetime, timedelta

# Configuración
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 100)
print("BUSCAR QUALITY CHECKS CON DEFECTOS REALES")
print("=" * 100)

# Buscar quality checks con hongos > 0 (cualquier variante del campo)
campos_hongos = ['x_studio_hongos', 'x_studio_hongos_1', 'x_studio_hongos_1_porcentaje']

for campo in campos_hongos:
    print(f"\nBuscando QCs con {campo} > 0...")
    try:
        qcs = models.execute_kw(db, uid, password,
            'quality.check', 'search_read',
            [[[campo, '>', 0]]],
            {'fields': ['id', 'create_date', campo], 'limit': 3, 'order': 'create_date desc'}
        )
        
        if qcs:
            print(f"  ✅ Encontrados {len(qcs)} quality checks")
            for qc in qcs:
                print(f"     ID: {qc['id']}, Fecha: {qc.get('create_date')}, {campo}: {qc.get(campo)}")
        else:
            print(f"  ❌ No se encontraron QCs con este campo > 0")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")

# Buscar el quality check más reciente con total_def_calidad > 0
print("\n" + "=" * 100)
print("BUSCAR QCs CON x_studio_total_def_calidad_1 > 0")
print("=" * 100)

qcs = models.execute_kw(db, uid, password,
    'quality.check', 'search_read',
    [[['x_studio_total_def_calidad_1', '>', 0]]],
    {'fields': ['id', 'create_date', 'x_studio_total_def_calidad_1', 
                'x_studio_hongos_1', 'x_studio_inmadura_1', 'x_studio_sobremadurez_1',
                'x_studio_deshidratado', 'x_studio_crumble', 'x_studio_tipo_de_fruta',
                'x_studio_calific_final'], 
     'limit': 5, 'order': 'create_date desc'}
)

if qcs:
    print(f"\n✅ Encontrados {len(qcs)} quality checks con defectos")
    for qc in qcs:
        print(f"\nQuality Check ID: {qc['id']}")
        print(f"  Fecha: {qc.get('create_date')}")
        print(f"  Tipo fruta: {qc.get('x_studio_tipo_de_fruta')}")
        print(f"  Calificación: {qc.get('x_studio_calific_final')}")
        print(f"  Total defectos: {qc.get('x_studio_total_def_calidad_1')} g")
        print(f"  Hongos: {qc.get('x_studio_hongos_1')} g")
        print(f"  Inmadura: {qc.get('x_studio_inmadura_1')} g")
        print(f"  Sobremadura: {qc.get('x_studio_sobremadurez_1')} g")
        print(f"  Deshidratado: {qc.get('x_studio_deshidratado')} g")
        print(f"  Crumble: {qc.get('x_studio_crumble')} g")
        
    # Analizar el primero en detalle
    print("\n" + "=" * 100)
    print(f"ANÁLISIS DETALLADO QC ID: {qcs[0]['id']}")
    print("=" * 100)
    
    qc_detail = models.execute_kw(db, uid, password,
        'quality.check', 'read',
        [qcs[0]['id']],
        {'fields': []}
    )[0]
    
    # Mostrar todos los campos x_studio con valores > 0
    defectos = {}
    for field, value in sorted(qc_detail.items()):
        if field.startswith('x_studio') and isinstance(value, (int, float)) and value > 0:
            defectos[field] = value
    
    print("\nCAMPOS CON VALORES > 0:")
    for field, value in sorted(defectos.items()):
        print(f"  {field:50} = {value}")
else:
    print("\n❌ No se encontraron quality checks con x_studio_total_def_calidad_1 > 0")
    
    # Intentar con el campo sin _1
    print("\nIntentando con x_studio_total_def_calidad (sin _1)...")
    qcs = models.execute_kw(db, uid, password,
        'quality.check', 'search_read',
        [[['x_studio_total_def_calidad', '>', 0]]],
        {'fields': ['id', 'create_date', 'x_studio_total_def_calidad'], 
         'limit': 3, 'order': 'create_date desc'}
    )
    
    if qcs:
        print(f"  ✅ Encontrados {len(qcs)} QCs")
        for qc in qcs:
            print(f"     ID: {qc['id']}, Total defectos: {qc.get('x_studio_total_def_calidad')}")
    else:
        print("  ❌ Tampoco se encontraron con este campo")
