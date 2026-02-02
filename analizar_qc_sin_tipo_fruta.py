"""
Analizar quality checks SIN tipo de fruta (False) que pueden tener los datos de calidad
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
print("ANÁLISIS QUALITY CHECKS SIN TIPO DE FRUTA (False)")
print("=" * 100)

# Buscar quality checks recientes sin tipo de fruta
qcs = models.execute_kw(db, uid, password,
    'quality.check', 'search_read',
    [[['create_date', '>=', '2026-01-26'], 
      ['create_date', '<=', '2026-02-02'],
      '|', ['x_studio_tipo_de_fruta', '=', False], ['x_studio_tipo_de_fruta', '=', '']]],
    {'fields': [], 'limit': 5, 'order': 'create_date desc'}
)

print(f"\n✅ Encontrados {len(qcs)} quality checks sin tipo de fruta")

if qcs:
    for idx, qc in enumerate(qcs):
        print("\n" + "=" * 100)
        print(f"QUALITY CHECK #{idx+1} - ID: {qc['id']}")
        print("=" * 100)
        print(f"Fecha: {qc.get('create_date')}")
        
        # Buscar TODOS los campos x_studio con valores != False, 0, ''
        campos_con_valor = {}
        for field, value in sorted(qc.items()):
            if not field.startswith('x_studio'):
                continue
            if value in [False, '', 0, 0.0, []]:
                continue
            if isinstance(value, str) and len(value) > 100:
                continue  # Saltar textos muy largos
            campos_con_valor[field] = value
        
        if campos_con_valor:
            print(f"\n✅ Campos x_studio con valores ({len(campos_con_valor)} campos):")
            for field, value in sorted(campos_con_valor.items()):
                print(f"  {field:50} = {value}")
        else:
            print("\n⚠️  NO HAY CAMPOS x_studio CON VALORES")
        
        # Verificar campos específicos de calidad
        campos_calidad = {
            'Pallet': qc.get('x_studio_n_de_palet_o_paquete'),
            'Productor': qc.get('x_studio_productor') or qc.get('x_studio_productor_1'),
            'Guía': qc.get('x_studio_gua_de_despacho'),
            'Kg recepcionados': qc.get('x_studio_kg_recepcionados'),
            'Total defectos _1': qc.get('x_studio_total_def_calidad_1'),
            'Total defectos': qc.get('x_studio_total_def_calidad'),
            'Hongos _1': qc.get('x_studio_hongos_1'),
            'Hongos': qc.get('x_studio_hongos'),
            'Inmadura _1': qc.get('x_studio_inmadura_1'),
            'Inmadura': qc.get('x_studio_inmadura'),
        }
        
        print(f"\n📊 Campos clave de calidad:")
        for nombre, valor in campos_calidad.items():
            if valor not in [False, None, 0, 0.0, '']:
                print(f"  {nombre:25} = {valor}")

    # Buscar el tipo de control que son
    print("\n" + "=" * 100)
    print("IDENTIFICANDO TIPO DE CONTROL")
    print("=" * 100)
    
    qc_sample = qcs[0]
    titulo = qc_sample.get('x_studio_titulo_control_calidad')
    related = qc_sample.get('x_studio_related_field_j9bxJ')
    
    print(f"Título control: {titulo}")
    print(f"Related field: {related}")
    
    # Ver TODOS los campos no x_studio
    print("\nCAMPOS ESTÁNDAR:")
    for field, value in sorted(qc_sample.items()):
        if field.startswith('x_studio') or field.startswith('__'):
            continue
        if value in [False, None, '', 0, []]:
            continue
        if isinstance(value, (list, dict)):
            continue
        print(f"  {field:40} = {value}")
        
else:
    print("\n❌ No se encontraron quality checks sin tipo de fruta")
