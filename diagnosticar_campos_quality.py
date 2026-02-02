"""
Diagnóstico de campos quality.check para identificar el problema de defectos en 0
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
print("DIAGNÓSTICO CAMPOS QUALITY CHECK")
print("=" * 100)

# Buscar quality checks recientes
fecha_desde = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

qcs = models.execute_kw(db, uid, password,
    'quality.check', 'search_read',
    [[['create_date', '>=', fecha_desde]]],
    {'fields': [], 'limit': 5, 'order': 'create_date desc'}
)

if not qcs:
    print("❌ No se encontraron quality checks recientes")
    exit(1)

print(f"\n✅ Encontrados {len(qcs)} quality checks recientes")
print("\nAnalizando campos disponibles en primer quality check:")
print("-" * 100)

qc = qcs[0]
print(f"\nQuality Check ID: {qc['id']}")
print(f"Fecha creación: {qc.get('create_date', 'N/A')}")

# Filtrar solo campos x_studio que contengan valores
defect_fields = {}
percentage_fields = {}
other_fields = {}

for field, value in sorted(qc.items()):
    if not field.startswith('x_studio'):
        continue
    
    # Saltar campos vacíos
    if value in [False, '', None, 0, []]:
        continue
        
    # Clasificar por tipo de campo
    if any(keyword in field.lower() for keyword in ['hongos', 'inmadura', 'sobremadura', 'deshidratado', 
                                                      'crumble', 'mecanico', 'insecto', 'deform', 
                                                      'verde', 'herida', 'partida', 'materia', 'extrana']):
        defect_fields[field] = value
    elif any(keyword in field.lower() for keyword in ['iqf', 'block', 'total', 'def']):
        percentage_fields[field] = value
    else:
        other_fields[field] = value

print("\n" + "=" * 100)
print("CAMPOS DE DEFECTOS (con valores):")
print("=" * 100)
if defect_fields:
    for field, value in sorted(defect_fields.items()):
        print(f"  {field:50} = {value}")
else:
    print("  ⚠️  NO SE ENCONTRARON CAMPOS DE DEFECTOS CON VALORES")

print("\n" + "=" * 100)
print("CAMPOS DE PORCENTAJES/TOTALES (con valores):")
print("=" * 100)
if percentage_fields:
    for field, value in sorted(percentage_fields.items()):
        print(f"  {field:50} = {value}")
else:
    print("  ⚠️  NO SE ENCONTRARON CAMPOS DE PORCENTAJES CON VALORES")

print("\n" + "=" * 100)
print("OTROS CAMPOS STUDIO (con valores):")
print("=" * 100)
if other_fields:
    for field, value in sorted(other_fields.items()):
        if len(str(value)) < 100:  # Solo mostrar valores no muy largos
            print(f"  {field:50} = {value}")
else:
    print("  ⚠️  NO SE ENCONTRARON OTROS CAMPOS CON VALORES")

print("\n" + "=" * 100)
print("TODOS LOS CAMPOS x_studio (incluso vacíos):")
print("=" * 100)
all_studio = [(f, v) for f, v in sorted(qc.items()) if f.startswith('x_studio')]
for field, value in all_studio:
    print(f"  {field:50} = {value}")

print("\n" + "=" * 100)
print("ANÁLISIS COMPLETADO")
print("=" * 100)
