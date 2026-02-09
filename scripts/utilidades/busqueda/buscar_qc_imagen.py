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
print("BUSCAR QUALITY CHECK ESPECÍFICO DEL 30/01/2026 18:55")
print("=" * 100)

# Buscar quality checks del 30/01/2026 alrededor de las 18:55
qcs = models.execute_kw(db, uid, password,
    'quality.check', 'search_read',
    [[['create_date', '>=', '2026-01-30 18:00:00'], 
      ['create_date', '<=', '2026-01-30 19:30:00']]],
    {'fields': [], 'order': 'create_date asc'}
)

print(f"\n✅ Encontrados {len(qcs)} quality checks en ese rango horario")

for qc in qcs:
    print("\n" + "=" * 100)
    print(f"QC ID: {qc['id']} | Fecha: {qc.get('create_date')}")
    print("=" * 100)
    
    # Mostrar TODOS los campos x_studio con valores
    print("\nCAMPOS x_studio CON VALORES:")
    for field, value in sorted(qc.items()):
        if not field.startswith('x_studio'):
            continue
        if value in [False, '', 0, 0.0, []]:
            continue
        print(f"  {field:60} = {value}")
    
    # Ver si tiene los campos de defectos en gramos
    defectos_grs = {
        'Fruta Verde': qc.get('x_studio_fruta_verde') or qc.get('x_studio_fruta_verde_1'),
        'Decoloración': qc.get('x_studio_frutos_con_decoloracion') or qc.get('x_studio_frutos_con_decoloracin'),
        'Sobremadura': qc.get('x_studio_frutos_con_sobre_madurez_y_exudacion') or qc.get('x_studio_frutos_con_sobre_madurez_y_exudacin'),
        'Deshidratado': qc.get('x_studio_deshidratado') or qc.get('x_studio_deshidratado_1'),
        'Hongos': qc.get('x_studio_hongos') or qc.get('x_studio_hongos_1'),
        'Total Defectos %': qc.get('x_studio_total_defectos_'),
    }
    
    print("\n📊 DEFECTOS IDENTIFICADOS:")
    for nombre, valor in defectos_grs.items():
        if valor not in [False, None, 0, 0.0, '']:
            print(f"  {nombre:25} = {valor}")
