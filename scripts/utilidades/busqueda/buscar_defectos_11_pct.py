"""
Buscar quality checks con Total Defectos % = 11.1%
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
print("BUSCAR QUALITY CHECKS CON DEFECTOS ~11%")
print("=" * 100)

# Buscar todos los campos que puedan contener ese 11.1%
# Probablemente está en algún campo de porcentaje

# Primero buscar QCs de enero 2026
qcs = models.execute_kw(db, uid, password,
    'quality.check', 'search_read',
    [[['create_date', '>=', '2026-01-01'], ['create_date', '<=', '2026-02-05']]],
    {'fields': [], 'limit': 500}
)

print(f"\n✅ Analizando {len(qcs)} quality checks de enero-febrero 2026...")

# Buscar aquellos que tengan algún campo con valor ~11
encontrados = []
for qc in qcs:
    for field, value in qc.items():
        if isinstance(value, (int, float)):
            # Buscar valores entre 11.0 y 11.2
            if 11.0 <= value <= 11.5:
                if field.startswith('x_studio') and ('def' in field.lower() or 'tot' in field.lower()):
                    encontrados.append({
                        'id': qc['id'],
                        'fecha': qc.get('create_date'),
                        'campo': field,
                        'valor': value,
                        'tipo_fruta': qc.get('x_studio_tipo_de_fruta'),
                        'guia': qc.get('x_studio_gua_de_despacho')
                    })

if encontrados:
    print(f"\n✅ Encontrados {len(encontrados)} registros con valores ~11:")
    for item in encontrados[:20]:
        print(f"\nQC ID: {item['id']} | Fecha: {item['fecha']}")
        print(f"  Fruta: {item['tipo_fruta']} | Guía: {item['guia']}")
        print(f"  Campo: {item['campo']}")
        print(f"  Valor: {item['valor']}")
        
    # Analizar el primero en detalle
    if encontrados:
        print("\n" + "=" * 100)
        print(f"ANÁLISIS DETALLADO QC ID: {encontrados[0]['id']}")
        print("=" * 100)
        
        qc_detail = models.execute_kw(db, uid, password,
            'quality.check', 'read',
            [encontrados[0]['id']],
            {'fields': []}
        )[0]
        
        print(f"\nFecha: {qc_detail.get('create_date')}")
        print(f"Tipo fruta: {qc_detail.get('x_studio_tipo_de_fruta')}")
        print(f"Guía: {qc_detail.get('x_studio_gua_de_despacho')}")
        
        print("\nCAMPOS CON VALORES:")
        for field, value in sorted(qc_detail.items()):
            if not field.startswith('x_studio'):
                continue
            if value in [False, None, '', 0, 0.0, []]:
                continue
            if isinstance(value, str) and len(value) > 100:
                continue
            print(f"  {field:60} = {value}")
else:
    print("\n❌ No se encontraron QCs con valores ~11")
    
    # Buscar por otros campos que puedan indicar defectos
    print("\n" + "=" * 100)
    print("BUSCANDO CAMPOS QUE CONTENGAN 'DEFECT' Y TENGAN VALORES > 0")
    print("=" * 100)
    
    for qc in qcs[:50]:  # Primeros 50
        defectos_encontrados = []
        for field, value in qc.items():
            if field.startswith('x_studio') and 'def' in field.lower():
                if isinstance(value, (int, float)) and value > 0:
                    defectos_encontrados.append((field, value))
        
        if defectos_encontrados:
            print(f"\nQC ID: {qc['id']} | Fecha: {qc.get('create_date')[:16]} | Fruta: {qc.get('x_studio_tipo_de_fruta')}")
            for field, value in defectos_encontrados:
                print(f"  {field:60} = {value}")
