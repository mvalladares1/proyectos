"""
Leer la tabla hijo (one2many) donde están los defectos
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
print("ANALIZAR ESTRUCTURA ONE2MANY DEL QUALITY CHECK")
print("=" * 100)

# Leer el QC completo
qc_id = 14311  # El de la imagen

qc = models.execute_kw(db, uid, password,
    'quality.check', 'read',
    [qc_id],
    {'fields': []}
)[0]

print(f"\nQuality Check ID: {qc_id}")
print(f"Tipo fruta: {qc.get('x_studio_tipo_de_fruta')}")
print(f"Guía: {qc.get('x_studio_gua_de_despacho')}")

# Buscar todos los campos one2many
print("\n" + "=" * 100)
print("CAMPOS ONE2MANY DISPONIBLES:")
print("=" * 100)

one2many_fields = {}
for field, value in sorted(qc.items()):
    if field.startswith('x_studio_one2many') and isinstance(value, list) and len(value) > 0:
        one2many_fields[field] = value
        print(f"\n{field}:")
        print(f"  Registros: {value}")
        print(f"  Total: {len(value)} registros")

if not one2many_fields:
    print("\n⚠️  NO HAY CAMPOS ONE2MANY CON REGISTROS")
    print("\nVamos a buscar el modelo relacionado en los metadatos del campo...")
    
    # Leer los fields del modelo quality.check
    fields_info = models.execute_kw(db, uid, password,
        'ir.model.fields', 'search_read',
        [[['model', '=', 'quality.check'], ['name', 'like', 'one2many']]],
        {'fields': ['name', 'ttype', 'relation', 'relation_field']}
    )
    
    print(f"\n✅ Campos one2many en quality.check:")
    for field_info in fields_info:
        print(f"\n  Campo: {field_info['name']}")
        print(f"  Tipo: {field_info['ttype']}")
        print(f"  Modelo relacionado: {field_info.get('relation')}")
        print(f"  Campo inverso: {field_info.get('relation_field')}")
    
else:
    print("\n" + "=" * 100)
    print("INTENTANDO DETERMINAR EL MODELO DE LA RELACIÓN")
    print("=" * 100)
    
    # Leer metadata del campo one2many para saber el modelo
    for field_name, ids in one2many_fields.items():
        print(f"\nCampo: {field_name}")
        
        # Buscar el campo en ir.model.fields
        field_info = models.execute_kw(db, uid, password,
            'ir.model.fields', 'search_read',
            [[['model', '=', 'quality.check'], ['name', '=', field_name]]],
            {'fields': ['name', 'ttype', 'relation', 'relation_field'], 'limit': 1}
        )
        
        if field_info:
            related_model = field_info[0].get('relation')
            print(f"  Modelo relacionado: {related_model}")
            
            if related_model:
                # Leer los registros del modelo relacionado
                print(f"\n  Leyendo registros del modelo {related_model}...")
                try:
                    records = models.execute_kw(db, uid, password,
                        related_model, 'read',
                        [ids],
                        {'fields': []}
                    )
                    
                    print(f"  ✅ Registros encontrados: {len(records)}")
                    for rec in records:
                        print(f"\n  {'='*80}")
                        print(f"  Registro ID: {rec['id']}")
                        print(f"  {'='*80}")
                        
                        # Mostrar todos los campos con valores
                        for f, v in sorted(rec.items()):
                            if v not in [False, None, '', 0, 0.0, []]:
                                if isinstance(v, str) and len(v) > 100:
                                    continue
                                print(f"    {f:50} = {v}")
                                
                except Exception as e:
                    print(f"  ❌ Error leyendo registros: {e}")
