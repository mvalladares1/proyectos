"""
Buscar quality check por referencia QC15024 de la imagen
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
print("BUSCAR QUALITY CHECK POR REFERENCIA QC15024")
print("=" * 100)

# Buscar por nombre
qcs = models.execute_kw(db, uid, password,
    'quality.check', 'search_read',
    [[['name', 'ilike', 'QC15024']]],
    {'fields': [], 'limit': 1}
)

if not qcs:
    print("\n❌ No se encontró QC15024, buscando por ID cercano...")
    # Buscar ID 15024 directamente
    try:
        qcs = models.execute_kw(db, uid, password,
            'quality.check', 'read',
            [[15024]],
            {'fields': []}
        )
    except:
        qcs = []

if qcs:
    qc = qcs[0]
    print(f"\n✅ ENCONTRADO QC ID: {qc['id']}")
    print(f"Nombre: {qc.get('name')}")
    print(f"Fecha creación: {qc.get('create_date')}")
    print(f"Título: {qc.get('x_studio_titulo_control_calidad')}")
    
    print("\n" + "=" * 100)
    print("TODOS LOS CAMPOS x_studio CON VALORES")
    print("=" * 100)
    
    for field, value in sorted(qc.items()):
        if not field.startswith('x_studio'):
            continue
        if value in [False, '', 0, 0.0, []]:
            continue
        if isinstance(value, str) and len(value) > 150:
            continue
        print(f"  {field:65} = {value}")
    
    # Buscar específicamente campos de defectos en gramos
    print("\n" + "=" * 100)
    print("CAMPOS DE DEFECTOS")
    print("=" * 100)
    
    # Todos los posibles campos de defectos
    campos_defectos = [
        'x_studio_total_defectos_', 'x_studio_total_defectos',
        'x_studio_fruta_verde', 'x_studio_fruta_verde_1',
        'x_studio_frutos_con_decoloracin', 'x_studio_frutos_con_decoloracion',
        'x_studio_frutos_con_sobre_madurez_y_exudacin', 'x_studio_frutos_con_sobre_madurez_y_exudacion',
        'x_studio_frutos_con_sobremadura_y_exudacin', 'x_studio_frutos_con_sobremadurez_y_exudacion',
        'x_studio_deshidratado', 'x_studio_deshidratado_1',
        'x_studio_hongos', 'x_studio_hongos_1',
        'x_studio_material_vegetal', 'x_studio_materia_vegetal',
        'x_studio_materia_extraa', 'x_studio_materias_extraas',
        'x_studio_frutos_con_pedicelo', 'x_studio_frutos_con_pedicelo_1',
    ]
    
    for campo in campos_defectos:
        valor = qc.get(campo)
        if valor not in [False, None, 0, 0.0, '', []]:
            print(f"  {campo:65} = {valor}")
    
    # Buscar líneas de calidad (one2many)
    print("\n" + "=" * 100)
    print("LÍNEAS DE CALIDAD (one2many)")
    print("=" * 100)
    
    campos_one2many = [
        'x_studio_one2many_field_3jSXq',
        'x_studio_one2many_field_eNeCg', 
        'x_studio_one2many_field_ipdDS',
        'x_studio_one2many_field_mZmK2',
        'x_studio_one2many_field_nsxt0',
        'x_studio_one2many_field_RdQtm',
        'x_studio_one2many_field_rgA7I',
        'x_studio_one2many_field_vloaS',
    ]
    
    for campo_o2m in campos_one2many:
        lineas_ids = qc.get(campo_o2m)
        if lineas_ids and len(lineas_ids) > 0:
            print(f"\n  {campo_o2m}: {len(lineas_ids)} líneas")
            print(f"    IDs: {lineas_ids[:5]}...")  # Primeros 5 IDs
            
else:
    print("\n❌ No se encontró el quality check")
