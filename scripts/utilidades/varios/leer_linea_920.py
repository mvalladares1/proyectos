"""
Leer la línea 920 del modelo x_quality_check_line_46726 que tenía el QC 10179
"""
import xmlrpc.client

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
print("LEER LÍNEA 920 DEL MODELO x_quality_check_line_46726")
print("=" * 100)

try:
    linea = models.execute_kw(db, uid, password,
        'x_quality_check_line_46726', 'read',
        [920],
        {'fields': []}
    )[0]
    
    print("\n✅ Línea encontrada!")
    print(f"ID: {linea['id']}")
    
    print("\nTODOS LOS CAMPOS:")
    for field, value in sorted(linea.items()):
        if value not in [False, None, '', [], 0, 0.0]:
            if isinstance(value, str) and len(value) > 100:
                continue
            print(f"  {field:60} = {value}")
            
except Exception as e:
    print(f"\n❌ Error: {e}")

# Ahora buscar en TODOS los modelos de líneas, las que tienen datos recientes
print("\n" + "=" * 100)
print("BUSCAR LÍNEAS RECIENTES EN TODOS LOS MODELOS")
print("=" * 100)

modelos_lineas = [
    'x_quality_check_line_2a594',
    'x_quality_check_line_0d011',
    'x_quality_check_line_35406',
    'x_quality_check_line_46726',
    'x_quality_check_line_17bfb',
    'x_quality_check_line_2efd1',
    'x_quality_check_line_1d183',
    'x_quality_check_line_f0f7b'
]

for modelo in modelos_lineas:
    print(f"\nModelo: {modelo}")
    try:
        # Buscar las líneas más recientes
        lineas = models.execute_kw(db, uid, password,
            modelo, 'search_read',
            [[['create_date', '>=', '2026-01-01']]],
            {'fields': ['id', 'create_date', 'x_quality_check_id'], 'limit': 5, 'order': 'create_date desc'}
        )
        
        if lineas:
            print(f"  ✅ {len(lineas)} líneas recientes")
            for linea in lineas:
                qc_ref = linea.get('x_quality_check_id')
                qc_id = qc_ref[0] if isinstance(qc_ref, (list, tuple)) else qc_ref
                print(f"    ID: {linea['id']:5} | Fecha: {linea.get('create_date')[:16]} | QC: {qc_id}")
        else:
            print(f"  - Sin líneas recientes")
            
    except Exception as e:
        print(f"  ⚠️  Error: {str(e)[:100]}")
