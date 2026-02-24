"""
Investigar reportes QWeb de factura de proveedor en Odoo
Objetivo: Obtener el template actual usado para imprimir facturas
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
print("INVESTIGACIÓN: REPORTES QWEB DE FACTURA PROVEEDOR")
print("=" * 100)

# ============================================================================
# PASO 1: Buscar reportes asociados a account.move
# ============================================================================
print("\n" + "=" * 100)
print("PASO 1: Reportes asociados a account.move (ir.actions.report)")
print("=" * 100)

reportes = models.execute_kw(db, uid, password,
    'ir.actions.report', 'search_read',
    [[['model', '=', 'account.move']]],
    {
        'fields': ['id', 'name', 'report_name', 'report_type', 'binding_model_id', 
                   'print_report_name', 'paperformat_id'],
        'order': 'name'
    }
)

print(f"\n✅ Encontrados {len(reportes)} reportes para account.move:")
for r in reportes:
    print(f"\n  ID: {r['id']}")
    print(f"    name:              {r['name']}")
    print(f"    report_name:       {r['report_name']}")
    print(f"    report_type:       {r['report_type']}")
    print(f"    print_report_name: {r['print_report_name']}")


# ============================================================================
# PASO 2: Buscar el template QWeb específico de factura
# ============================================================================
print("\n" + "=" * 100)
print("PASO 2: Buscar templates QWeb de factura (ir.ui.view)")
print("=" * 100)

# Buscar vistas QWeb relacionadas con invoices
templates = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[
        '|', '|', '|',
        ['name', 'ilike', 'invoice'],
        ['name', 'ilike', 'factura'],
        ['key', 'ilike', 'invoice'],
        ['key', 'ilike', 'account.report']
    ]],
    {
        'fields': ['id', 'name', 'key', 'type', 'model', 'inherit_id', 'mode', 'active'],
        'order': 'name',
        'limit': 50
    }
)

print(f"\n✅ Encontrados {len(templates)} templates relacionados con invoice:")
for t in templates:
    if t.get('type') == 'qweb':
        print(f"\n  ID: {t['id']}")
        print(f"    name:       {t['name']}")
        print(f"    key:        {t.get('key', '-')}")
        print(f"    type:       {t['type']}")
        print(f"    inherit_id: {t.get('inherit_id', '-')}")
        print(f"    active:     {t.get('active', '-')}")


# ============================================================================
# PASO 3: Buscar el template principal de factura
# ============================================================================
print("\n" + "=" * 100)
print("PASO 3: Template principal de factura (report_invoice_document)")
print("=" * 100)

# Buscar el template base de factura
main_templates = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[
        '|', '|', '|', '|',
        ['key', 'ilike', 'report_invoice'],
        ['key', 'ilike', 'account.report_invoice'],
        ['name', 'ilike', 'report_invoice'],
        ['name', '=', 'account.report_invoice_document'],
        ['key', '=', 'account.report_invoice_document'],
    ]],
    {
        'fields': ['id', 'name', 'key', 'type', 'arch_db', 'inherit_id', 'active'],
        'order': 'id'
    }
)

print(f"\n✅ Templates principales encontrados: {len(main_templates)}")
for t in main_templates:
    print(f"\n  ID: {t['id']}")
    print(f"    name:       {t['name']}")
    print(f"    key:        {t.get('key', '-')}")
    print(f"    type:       {t['type']}")
    print(f"    inherit_id: {t.get('inherit_id', '-')}")
    
    # Mostrar primeras líneas del arch_db si existe
    arch = t.get('arch_db', '')
    if arch and len(arch) > 0:
        print(f"    arch_db (primeros 500 chars):")
        print(f"    {arch[:500]}...")


# ============================================================================
# PASO 4: Obtener el contenido completo del template de factura
# ============================================================================
print("\n" + "=" * 100)
print("PASO 4: Contenido del template principal de factura")
print("=" * 100)

# Buscar específicamente el template de documento de factura
invoice_doc = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[['key', '=', 'account.report_invoice_document']]],
    {'fields': ['id', 'name', 'key', 'arch_db', 'inherit_id']}
)

if not invoice_doc:
    # Intentar con otros nombres comunes
    invoice_doc = models.execute_kw(db, uid, password,
        'ir.ui.view', 'search_read',
        [[['name', 'ilike', 'report_invoice_document']]],
        {'fields': ['id', 'name', 'key', 'arch_db', 'inherit_id']}
    )

if invoice_doc:
    print(f"\n✅ Template encontrado: {invoice_doc[0]['name']}")
    print(f"   ID: {invoice_doc[0]['id']}")
    print(f"   Key: {invoice_doc[0].get('key', '-')}")
    
    # Guardar el contenido en un archivo
    arch = invoice_doc[0].get('arch_db', '')
    if arch:
        with open('template_factura_actual.xml', 'w', encoding='utf-8') as f:
            f.write(arch)
        print(f"\n📄 Template guardado en: template_factura_actual.xml")
        print(f"   Tamaño: {len(arch)} caracteres")
else:
    print("\n⚠️  No se encontró el template report_invoice_document")
    print("    Buscando templates personalizados...")


# ============================================================================
# PASO 5: Buscar herencias/personalizaciones del template
# ============================================================================
print("\n" + "=" * 100)
print("PASO 5: Herencias del template de factura (personalizaciones)")
print("=" * 100)

if invoice_doc:
    base_id = invoice_doc[0]['id']
    
    herencias = models.execute_kw(db, uid, password,
        'ir.ui.view', 'search_read',
        [[['inherit_id', '=', base_id]]],
        {'fields': ['id', 'name', 'key', 'arch_db', 'active', 'priority']}
    )
    
    print(f"\n✅ Herencias encontradas: {len(herencias)}")
    for h in herencias:
        print(f"\n  ID: {h['id']}")
        print(f"    name:     {h['name']}")
        print(f"    key:      {h.get('key', '-')}")
        print(f"    active:   {h.get('active', True)}")
        print(f"    priority: {h.get('priority', '-')}")
        
        # Guardar cada herencia
        arch = h.get('arch_db', '')
        if arch:
            filename = f"template_herencia_{h['id']}.xml"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(arch)
            print(f"    📄 Guardado en: {filename}")


# ============================================================================
# PASO 6: Buscar templates Studio (personalizados)
# ============================================================================
print("\n" + "=" * 100)
print("PASO 6: Templates personalizados por Studio")
print("=" * 100)

studio_templates = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[
        ['key', 'ilike', 'studio'],
        ['type', '=', 'qweb'],
        '|',
        ['name', 'ilike', 'invoice'],
        ['name', 'ilike', 'account']
    ]],
    {'fields': ['id', 'name', 'key', 'inherit_id', 'active']}
)

print(f"\n✅ Templates Studio relacionados: {len(studio_templates)}")
for t in studio_templates:
    print(f"\n  ID: {t['id']}")
    print(f"    name:       {t['name']}")
    print(f"    key:        {t.get('key', '-')}")
    print(f"    inherit_id: {t.get('inherit_id', '-')}")


# ============================================================================
# RESUMEN: Reportes de impresión disponibles
# ============================================================================
print("\n" + "=" * 100)
print("RESUMEN: REPORTES DE IMPRESIÓN DISPONIBLES PARA FACTURAS")
print("=" * 100)

print("\n📊 Reportes (ir.actions.report) para account.move:")
for r in reportes:
    print(f"  • {r['name']}")
    print(f"    report_name: {r['report_name']}")

print("\n" + "=" * 100)
print("FIN DE INVESTIGACIÓN")
print("=" * 100)
