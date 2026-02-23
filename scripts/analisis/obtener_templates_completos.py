"""
Obtener template l10n_cl.informations para ver estructura actual
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
print("OBTENER TEMPLATES l10n_cl COMPLETOS")
print("=" * 100)

# Buscar template de informaciones de Chile
templates_cl = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[
        ['key', 'like', 'l10n_cl.%'],
        ['type', '=', 'qweb']
    ]],
    {
        'fields': ['id', 'name', 'key', 'arch_db', 'inherit_id'],
        'order': 'key'
    }
)

print(f"\n✅ Templates l10n_cl encontrados: {len(templates_cl)}")

for t in templates_cl:
    key = t.get('key', '')
    if 'information' in key.lower() or 'report_invoice' in key.lower():
        print(f"\n{'=' * 80}")
        print(f"Template: {t['key']}")
        print(f"ID: {t['id']}")
        print(f"Name: {t['name']}")
        print(f"{'=' * 80}")
        
        arch = t.get('arch_db', '')
        if arch:
            # Guardar archivo
            safe_name = key.replace('.', '_').replace('/', '_')
            filename = f"template_{safe_name}.xml"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(arch)
            print(f"📄 Guardado: {filename}")
            print(f"Tamaño: {len(arch)} chars")
            
            # Mostrar primeras líneas
            print("\nContenido:")
            print(arch[:2000])
            print("..." if len(arch) > 2000 else "")


# Buscar también Original Bills template
print("\n" + "=" * 100)
print("TEMPLATE: Original Bills (factura proveedor)")
print("=" * 100)

original_bills = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[
        '|',
        ['key', 'ilike', 'vendor_bill'],
        ['key', 'ilike', 'original_vendor']
    ]],
    {
        'fields': ['id', 'name', 'key', 'arch_db', 'inherit_id'],
        'order': 'key'
    }
)

for t in original_bills:
    print(f"\n{'=' * 80}")
    print(f"Template: {t.get('key')}")
    print(f"ID: {t['id']}")
    print(f"Name: {t['name']}")
    print(f"inherit_id: {t.get('inherit_id')}")
    print(f"{'=' * 80}")
    
    arch = t.get('arch_db', '')
    if arch:
        filename = f"template_vendor_bill_{t['id']}.xml"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(arch)
        print(f"📄 Guardado: {filename}")
        print("\nContenido:")
        print(arch[:3000])


# Buscar herencias del template de vendor bill
print("\n" + "=" * 100)
print("HERENCIAS DE account.report_original_vendor_bill")
print("=" * 100)

# Primero obtener el ID del template original_vendor_bill
vendor_base = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[['key', '=', 'account.report_original_vendor_bill']]],
    {'fields': ['id', 'name', 'key']}
)

if vendor_base:
    base_id = vendor_base[0]['id']
    print(f"\nTemplate base ID: {base_id}")
    
    herencias = models.execute_kw(db, uid, password,
        'ir.ui.view', 'search_read',
        [[['inherit_id', '=', base_id]]],
        {'fields': ['id', 'name', 'key', 'arch_db', 'active']}
    )
    
    print(f"Herencias encontradas: {len(herencias)}")
    for h in herencias:
        print(f"\n  ID: {h['id']}")
        print(f"  name: {h['name']}")
        print(f"  key: {h.get('key', '-')}")
        
        arch = h.get('arch_db', '')
        if arch:
            filename = f"template_vendor_bill_herencia_{h['id']}.xml"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(arch)
            print(f"  📄 Guardado: {filename}")
