"""
Leer líneas recientes completas para ver estructura de defectos
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
print("LEER LÍNEAS RECIENTES COMPLETAS")
print("=" * 100)

# Leer línea 3304 del modelo x_quality_check_line_46726
linea_id = 3304
try:
    linea = models.execute_kw(db, uid, password,
        'x_quality_check_line_46726', 'read',
        [linea_id],
        {'fields': []}
    )[0]
    
    print(f"\n✅ Línea {linea_id} - Modelo x_quality_check_line_46726")
    print(f"QC: {linea.get('x_quality_check_id')}")
    print(f"Fecha: {linea.get('create_date')}")
    
    print("\nCAMPOS CON VALORES:")
    for field, value in sorted(linea.items()):
        if value not in [False, None, '', [], 0, 0.0]:
            if isinstance(value, str) and len(value) > 100:
                continue
            print(f"  {field:60} = {value}")
            
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 100)

# Leer línea 84 del modelo x_quality_check_line_0d011
linea_id = 84
try:
    linea = models.execute_kw(db, uid, password,
        'x_quality_check_line_0d011', 'read',
        [linea_id],
        {'fields': []}
    )[0]
    
    print(f"\n✅ Línea {linea_id} - Modelo x_quality_check_line_0d011")
    print(f"QC: {linea.get('x_quality_check_id')}")
    print(f"Fecha: {linea.get('create_date')}")
    
    print("\nCAMPOS CON VALORES:")
    for field, value in sorted(linea.items()):
        if value not in [False, None, '', [], 0, 0.0]:
            if isinstance(value, str) and len(value) > 100:
                continue
            print(f"  {field:60} = {value}")
            
except Exception as e:
    print(f"❌ Error: {e}")

# Ahora leer el QC padre para entender la relación
print("\n" + "=" * 100)
print("LEER QC PADRE (15129)")
print("=" * 100)

try:
    qc = models.execute_kw(db, uid, password,
        'quality.check', 'read',
        [15129],
        {'fields': []}
    )[0]
    
    print(f"\nQC ID: 15129")
    print(f"Tipo fruta: {qc.get('x_studio_tipo_de_fruta')}")
    print(f"Guía: {qc.get('x_studio_gua_de_despacho')}")
    print(f"Calificación: {qc.get('x_studio_calific_final')}")
    
    print("\nCAMPOS ONE2MANY:")
    for field, value in sorted(qc.items()):
        if field.startswith('x_studio_one2many') and isinstance(value, list) and len(value) > 0:
            print(f"  {field:60} = {value} ({len(value)} registros)")
    
    print("\nCAMPOS DE DEFECTOS EN EL QC PRINCIPAL:")
    campos_defectos = ['x_studio_total_def_calidad_1', 'x_studio_hongos_1', 'x_studio_inmadura_1',
                       'x_studio_sobremadurez_1', 'x_studio_deshidratado']
    for campo in campos_defectos:
        valor = qc.get(campo)
        if valor not in [False, None, 0, 0.0]:
            print(f"  {campo:60} = {valor}")
            
except Exception as e:
    print(f"❌ Error: {e}")
