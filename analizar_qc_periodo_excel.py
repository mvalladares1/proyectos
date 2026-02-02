"""
Analizar quality checks de la fecha específica del Excel (2026-01-26 a 2026-02-02)
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
print("ANÁLISIS QUALITY CHECKS - PERÍODO DEL EXCEL")
print("=" * 100)

# Buscar quality checks entre 2026-01-26 y 2026-02-02
qcs = models.execute_kw(db, uid, password,
    'quality.check', 'search_read',
    [[['create_date', '>=', '2026-01-26'], ['create_date', '<=', '2026-02-02']]],
    {'fields': ['id', 'create_date', 'x_studio_tipo_de_fruta', 'x_studio_calific_final',
                'x_studio_total_def_calidad_1', 'x_studio_hongos_1', 'x_studio_inmadura_1',
                'x_studio_n_de_palet_o_paquete', 'x_studio_gua_de_despacho'], 
     'order': 'create_date desc'}
)

print(f"\n✅ Encontrados {len(qcs)} quality checks en el período")

if qcs:
    print("\nRESUMEN:")
    print("-" * 100)
    for qc in qcs:
        print(f"ID: {qc['id']:5} | Fecha: {qc.get('create_date')[:16]} | "
              f"Fruta: {str(qc.get('x_studio_tipo_de_fruta'))[:10]:10} | "
              f"Calif: {str(qc.get('x_studio_calific_final'))[:10]:10} | "
              f"Total Def: {qc.get('x_studio_total_def_calidad_1', 0):6.1f}g | "
              f"Pallet: {str(qc.get('x_studio_n_de_palet_o_paquete'))[:10]:10} | "
              f"Guía: {qc.get('x_studio_gua_de_despacho') or 'N/A'}")
    
    # Analizar uno en detalle
    print("\n" + "=" * 100)
    print(f"ANÁLISIS DETALLADO - QC ID: {qcs[0]['id']}")
    print("=" * 100)
    
    qc_detail = models.execute_kw(db, uid, password,
        'quality.check', 'read',
        [qcs[0]['id']],
        {'fields': []}
    )[0]
    
    # Mostrar TODOS los campos de defectos (con y sin _1)
    campos_defectos = [
        'x_studio_hongos', 'x_studio_hongos_1',
        'x_studio_inmadura', 'x_studio_inmadura_1',
        'x_studio_sobremadura', 'x_studio_sobremadurez_1',
        'x_studio_deshidratado', 'x_studio_deshidratado_1',
        'x_studio_crumble', 'x_studio_crumble_1',
        'x_studio_dao_mecanico', 'x_studio_dao_mecanico_1',
        'x_studio_presencia_de_insectos', 'x_studio_presencia_de_insectos_1',
        'x_studio_frutos_deformes', 'x_studio_frutos_deformes_1',
        'x_studio_fruta_verde', 'x_studio_fruta_verde_1',
        'x_studio_heridapartiduramolida', 'x_studio_heridapartidamolida', 'x_studio_heridapartidamolida_1',
        'x_studio_materias_extraas', 'x_studio_materias_extraas_1', 'x_studio_materias_extranas',
        'x_studio_total_def_calidad', 'x_studio_total_def_calidad_1',
        'x_studio_total_iqf_', 'x_studio_total_block_'
    ]
    
    print("\nCAMPOS DE DEFECTOS:")
    for campo in campos_defectos:
        valor = qc_detail.get(campo)
        if valor not in [False, None]:
            print(f"  {campo:50} = {valor}")
    
    # Verificar si hay valores en campos sin _1
    print("\n" + "=" * 100)
    print("COMPARACIÓN: ¿Usan _1 o sin _1?")
    print("=" * 100)
    
    with_1 = sum(1 for c in campos_defectos if '_1' in c and qc_detail.get(c) not in [False, None, 0, 0.0])
    without_1 = sum(1 for c in campos_defectos if '_1' not in c and 'total' not in c and qc_detail.get(c) not in [False, None, 0, 0.0])
    
    print(f"  Campos CON _1 con valores: {with_1}")
    print(f"  Campos SIN _1 con valores: {without_1}")
    
    if with_1 == 0 and without_1 == 0:
        print("\n  ⚠️  TODOS LOS DEFECTOS ESTÁN EN 0 - La fruta NO tenía defectos reales")
    elif with_1 > 0:
        print("\n  ✅ Usar campos con sufijo _1")
    elif without_1 > 0:
        print("\n  ✅ Usar campos SIN sufijo _1")
else:
    print("\n❌ No se encontraron quality checks en este período")
