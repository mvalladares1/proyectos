"""
Buscar el quality check específico de la imagen: 30/01/2026 18:55:26
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
print("BUSCAR QUALITY CHECK DEL 30/01/2026 18:55:26")
print("=" * 100)

# Buscar quality check en ese timestamp exacto
qcs = models.execute_kw(db, uid, password,
    'quality.check', 'search_read',
    [[['create_date', '>=', '2026-01-30 18:00:00'], 
      ['create_date', '<=', '2026-01-30 19:00:00']]],
    {'fields': [], 'order': 'create_date desc'}
)

print(f"\n✅ Encontrados {len(qcs)} quality checks en esa hora")

for qc in qcs:
    print(f"\n{'='*100}")
    print(f"QC ID: {qc['id']} - Fecha: {qc.get('create_date')}")
    print(f"{'='*100}")
    
    # Buscar TODOS los campos que contengan valores > 0
    print("\nCAMPOS CON VALORES > 0:")
    for field, value in sorted(qc.items()):
        if field.startswith('x_studio'):
            if isinstance(value, (int, float)) and value > 0:
                print(f"  {field:60} = {value}")
    
    # Campos específicos de la imagen
    print("\nCAMPOS ESPECÍFICOS DE LA IMAGEN:")
    campos_imagen = {
        'Muestra grs': qc.get('x_studio_gramos_de_la_muestra_1') or qc.get('x_studio_gramos_de_la_muestra'),
        'Total Defectos %': None,  # Buscar todos los que tengan 'defecto' y '%'
        'Fruta Verde(grs)': qc.get('x_studio_fruta_verde') or qc.get('x_studio_fruta_verde_1'),
        'Frutos decoloración': qc.get('x_studio_frutos_con_decoloracion') or qc.get('x_studio_frutos_con_decoloracin'),
        'Frutos sobre madurez': qc.get('x_studio_frutos_con_sobre_madurez_y_exudacin') or qc.get('x_studio_sobremadura') or qc.get('x_studio_sobremadurez_1'),
        'Deshidratado(grs)': qc.get('x_studio_deshidratado') or qc.get('x_studio_deshidratado_1'),
        'Materia Vegetal(grs)': qc.get('x_studio_materia_vegetal') or qc.get('x_studio_totmateriavegetal'),
    }
    
    for nombre, valor in campos_imagen.items():
        print(f"  {nombre:30} = {valor}")
    
    # Buscar campos que contengan 'total' y 'defect'
    print("\nCAMPOS CON 'TOTAL' Y 'DEFECT':")
    for field, value in sorted(qc.items()):
        if 'total' in field.lower() and 'def' in field.lower():
            print(f"  {field:60} = {value}")
    
    # Buscar campos de porcentajes
    print("\nCAMPOS CON PORCENTAJES (%):")
    for field, value in sorted(qc.items()):
        if field.startswith('x_studio') and ('porcentaje' in field.lower() or '_percent' in field.lower()):
            if value not in [False, 0, 0.0]:
                print(f"  {field:60} = {value}")
    
    # Ver si tiene relaciones one2many (líneas)
    print("\nCAMPOS ONE2MANY (relaciones):")
    for field, value in sorted(qc.items()):
        if field.startswith('x_studio') and isinstance(value, list) and len(value) > 0:
            print(f"  {field:60} = {value} ({len(value)} registros)")

print("\n" + "=" * 100)
print("BÚSQUEDA COMPLETADA")
print("=" * 100)
