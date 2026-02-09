"""
Buscar quality checks de RECEPCIÓN MP con título específico
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
print("BUSCAR QUALITY CHECKS DE RECEPCIÓN MP")
print("=" * 100)

# Buscar por título "Control de calidad Recepcion MP"
qcs_recepcion = models.execute_kw(db, uid, password,
    'quality.check', 'search_read',
    [[['create_date', '>=', '2026-01-26'], 
      ['create_date', '<=', '2026-02-02'],
      ['x_studio_titulo_control_calidad', 'ilike', 'Recepcion MP']]],
    {'fields': ['id', 'create_date', 'x_studio_tipo_de_fruta', 'x_studio_calific_final',
                'x_studio_gua_de_despacho', 'x_studio_total_def_calidad_1',
                'x_studio_hongos_1', 'x_studio_inmadura_1', 'x_studio_titulo_control_calidad'], 
     'order': 'create_date desc'}
)

print(f"\n✅ Encontrados {len(qcs_recepcion)} quality checks de Recepción MP")

if qcs_recepcion:
    print("\nRESUMEN:")
    print("-" * 100)
    for qc in qcs_recepcion[:20]:  # Primeros 20
        print(f"ID: {qc['id']:5} | Fecha: {qc.get('create_date')[:16]} | "
              f"Fruta: {str(qc.get('x_studio_tipo_de_fruta'))[:12]:12} | "
              f"Calif: {str(qc.get('x_studio_calific_final'))[:8]:8} | "
              f"Total Def: {qc.get('x_studio_total_def_calidad_1', 0):6.1f}g | "
              f"Hongos: {qc.get('x_studio_hongos_1', 0):5.1f}g | "
              f"Guía: {str(qc.get('x_studio_gua_de_despacho'))[:10]:10}")
    
    if len(qcs_recepcion) > 20:
        print(f"... y {len(qcs_recepcion) - 20} más")
    
    # Contar los que tienen defectos > 0
    with_defects = sum(1 for qc in qcs_recepcion if qc.get('x_studio_total_def_calidad_1', 0) > 0)
    print(f"\n📊 QCs con defectos > 0: {with_defects} de {len(qcs_recepcion)}")
    
    # Analizar uno en detalle
    print("\n" + "=" * 100)
    print(f"ANÁLISIS DETALLADO - Primer QC de Recepción MP (ID: {qcs_recepcion[0]['id']})")
    print("=" * 100)
    
    qc_detail = models.execute_kw(db, uid, password,
        'quality.check', 'read',
        [qcs_recepcion[0]['id']],
        {'fields': []}
    )[0]
    
    # Campos de defectos
    campos_defectos = {}
    for field, value in sorted(qc_detail.items()):
        if not field.startswith('x_studio'):
            continue
        if field in ['x_studio_hongos', 'x_studio_hongos_1', 'x_studio_inmadura', 'x_studio_inmadura_1',
                     'x_studio_sobremadura', 'x_studio_sobremadurez_1', 'x_studio_deshidratado',
                     'x_studio_crumble', 'x_studio_dao_mecanico', 'x_studio_presencia_de_insectos',
                     'x_studio_frutos_deformes', 'x_studio_fruta_verde', 'x_studio_heridapartidamolida',
                     'x_studio_materias_extraas', 'x_studio_total_def_calidad_1', 'x_studio_total_def_calidad']:
            campos_defectos[field] = value
    
    print("\nCAMPOS DE DEFECTOS:")
    for field, value in sorted(campos_defectos.items()):
        if value not in [False, None, 0, 0.0]:
            print(f"  {field:50} = {value}")
    
    # Otros campos importantes
    print("\nOTROS CAMPOS IMPORTANTES:")
    campos_importantes = ['x_studio_tipo_de_fruta', 'x_studio_calific_final', 'x_studio_gua_de_despacho',
                          'x_studio_n_de_palet_o_paquete', 'x_studio_kg_recepcionados',
                          'x_studio_gramos_de_la_muestra_1', 'x_studio_total_iqf_', 'x_studio_total_block_']
    for field in campos_importantes:
        value = qc_detail.get(field)
        if value not in [False, None, '', 0]:
            print(f"  {field:50} = {value}")

else:
    print("\n❌ No se encontraron quality checks de Recepción MP en este período")
    
    # Buscar sin filtro de título para ver qué hay
    print("\n" + "=" * 100)
    print("BUSCANDO TODOS LOS QC DEL PERÍODO (sin filtro de título)")
    print("=" * 100)
    
    all_qcs = models.execute_kw(db, uid, password,
        'quality.check', 'search_read',
        [[['create_date', '>=', '2026-01-26'], ['create_date', '<=', '2026-02-02']]],
        {'fields': ['id', 'x_studio_titulo_control_calidad'], 'limit': 10}
    )
    
    titulos = {}
    for qc in all_qcs:
        titulo = qc.get('x_studio_titulo_control_calidad') or 'Sin título'
        titulos[titulo] = titulos.get(titulo, 0) + 1
    
    print("\nTítulos encontrados:")
    for titulo, count in sorted(titulos.items(), key=lambda x: -x[1]):
        print(f"  {titulo:50} : {count} QCs")
