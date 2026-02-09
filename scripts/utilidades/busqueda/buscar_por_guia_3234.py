"""
Buscar quality check por guía de despacho 3234
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
print("BUSCAR QUALITY CHECK CON GUÍA 3234")
print("=" * 100)

# Buscar por guía
qcs = models.execute_kw(db, uid, password,
    'quality.check', 'search_read',
    [[['x_studio_gua_de_despacho', '=', '3234']]],
    {'fields': [], 'limit': 10}
)

print(f"\n✅ Encontrados {len(qcs)} quality checks con guía 3234")

if qcs:
    for qc in qcs:
        print(f"\n{'='*100}")
        print(f"QC ID: {qc['id']} - Fecha: {qc.get('create_date')}")
        print(f"Tipo fruta: {qc.get('x_studio_tipo_de_fruta')}")
        print(f"Calificación: {qc.get('x_studio_calific_final')}")
        print(f"{'='*100}")
        
        # TODOS los campos con valores
        print("\nTODOS LOS CAMPOS x_studio CON VALORES:")
        for field, value in sorted(qc.items()):
            if not field.startswith('x_studio'):
                continue
            if value in [False, '', 0, 0.0, []]:
                continue
            if isinstance(value, str) and len(value) > 100:
                continue
            print(f"  {field:60} = {value}")
        
        # Campos one2many
        print("\nCAMPOS ONE2MANY (tablas hijas):")
        for field, value in sorted(qc.items()):
            if field.startswith('x_studio_one2many') and isinstance(value, list) and len(value) > 0:
                print(f"\n  {field}: {len(value)} registros")
                print(f"  IDs: {value}")
                
                # Leer el primer registro de la relación para ver su estructura
                if value:
                    # Intentar determinar el modelo de la relación
                    # Por ahora solo mostrar los IDs
                    pass
else:
    print("\n❌ No se encontró quality check con guía 3234")
    
    # Buscar guías similares
    print("\nBuscando guías similares (323*)...")
    qcs_similar = models.execute_kw(db, uid, password,
        'quality.check', 'search_read',
        [[['x_studio_gua_de_despacho', 'ilike', '323']]],
        {'fields': ['id', 'x_studio_gua_de_despacho', 'create_date'], 'limit': 10}
    )
    
    if qcs_similar:
        print(f"\n✅ Encontradas {len(qcs_similar)} guías similares:")
        for qc in qcs_similar:
            print(f"  ID: {qc['id']:5} | Guía: {qc.get('x_studio_gua_de_despacho'):10} | Fecha: {qc.get('create_date')}")
