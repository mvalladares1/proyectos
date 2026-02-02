"""
Buscar líneas de quality check en los modelos one2many
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
print("BUSCAR LÍNEAS DE QUALITY CHECK")
print("=" * 100)

qc_id = 14311

# Modelos one2many de quality check
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
    print(f"\nBuscando en modelo: {modelo}")
    try:
        lineas = models.execute_kw(db, uid, password,
            modelo, 'search_read',
            [[['x_quality_check_id', '=', qc_id]]],
            {'fields': [], 'limit': 20}
        )
        
        if lineas:
            print(f"  ✅ Encontradas {len(lineas)} líneas!")
            for linea in lineas:
                print(f"\n  {'='*90}")
                print(f"  Línea ID: {linea['id']}")
                print(f"  {'='*90}")
                
                # Mostrar TODOS los campos
                for field, value in sorted(linea.items()):
                    if value not in [False, None, '', 0, 0.0, []]:
                        if isinstance(value, str) and len(value) > 100:
                            continue
                        print(f"    {field:50} = {value}")
        else:
            print(f"  - No hay líneas")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")

print("\n" + "=" * 100)
print("BÚSQUEDA COMPLETADA")
print("=" * 100)
