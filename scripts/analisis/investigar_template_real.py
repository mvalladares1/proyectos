"""
Investigar el template REAL usado para la factura FAC 000849
y corregir la columna FECHA RECEPCIÓN para mostrar fecha de OC
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
print("INVESTIGAR TEMPLATE REAL DE FACTURA PROVEEDOR")
print("=" * 100)

# ============================================================
# PASO 1: Buscar templates que tengan "FECHA RECEPCIÓN" o "FECHA RECEPCION"
# ============================================================
print("\n" + "-" * 80)
print("PASO 1: Buscar templates con 'FECHA RECEPCIÓN'")
print("-" * 80)

templates = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[
        ['type', '=', 'qweb'],
        '|',
        ['arch_db', 'ilike', 'FECHA RECEPCI'],
        ['arch_db', 'ilike', 'fecha recepci']
    ]],
    {'fields': ['id', 'name', 'key', 'inherit_id', 'active'], 'limit': 20}
)

print(f"\n✅ Templates encontrados: {len(templates)}")
for t in templates:
    print(f"\n  ID: {t['id']}")
    print(f"  name: {t['name']}")
    print(f"  key: {t.get('key', '-')}")
    print(f"  inherit_id: {t.get('inherit_id', '-')}")

# ============================================================
# PASO 2: Buscar templates con "REFERENCIA DEL PEDIDO" (que aparece en el PDF)
# ============================================================
print("\n" + "-" * 80)
print("PASO 2: Buscar templates con 'REFERENCIA DEL PEDIDO'")
print("-" * 80)

templates2 = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[
        ['type', '=', 'qweb'],
        ['arch_db', 'ilike', 'REFERENCIA DEL PEDIDO']
    ]],
    {'fields': ['id', 'name', 'key', 'inherit_id'], 'limit': 20}
)

print(f"\n✅ Templates encontrados: {len(templates2)}")
for t in templates2:
    print(f"\n  ID: {t['id']}")
    print(f"  name: {t['name']}")
    print(f"  key: {t.get('key', '-')}")

# ============================================================
# PASO 3: Ver el template completo que tiene GUÍA/REFERENCIA/FECHA RECEPCIÓN
# ============================================================
print("\n" + "-" * 80)
print("PASO 3: Obtener contenido de templates relevantes")
print("-" * 80)

# Combinar IDs únicos
all_ids = list(set([t['id'] for t in templates] + [t['id'] for t in templates2]))

for template_id in all_ids[:5]:  # Primeros 5
    template = models.execute_kw(db, uid, password,
        'ir.ui.view', 'read',
        [[template_id]],
        {'fields': ['id', 'name', 'key', 'arch_db']}
    )
    
    if template:
        t = template[0]
        arch = t.get('arch_db', '')
        
        # Guardar
        safe_name = f"template_real_{t['id']}.xml"
        with open(safe_name, 'w', encoding='utf-8') as f:
            f.write(arch)
        
        print(f"\n📄 Template ID: {t['id']} ({t['name']})")
        print(f"   Key: {t.get('key', '-')}")
        print(f"   Guardado: {safe_name}")
        
        # Buscar la sección relevante
        if 'FECHA RECEPCI' in arch.upper() or 'REFERENCIA DEL PEDIDO' in arch:
            print(f"   ⭐ CONTIENE COLUMNAS DE INTERÉS")
            
            # Mostrar fragmento relevante
            import re
            # Buscar la tabla con las columnas
            if 'GUÍA' in arch or 'FECHA RECEPCI' in arch.upper():
                print(f"\n   📋 Fragmento relevante:")
                # Encontrar la línea con FECHA
                lines = arch.split('\n')
                for i, line in enumerate(lines):
                    if 'FECHA' in line.upper() and 'RECEPCI' in line.upper():
                        start = max(0, i-5)
                        end = min(len(lines), i+10)
                        print('\n'.join(lines[start:end]))
                        break


# ============================================================
# PASO 4: Buscar específicamente el reporte que se usa para in_invoice Chile
# ============================================================
print("\n" + "-" * 80)
print("PASO 4: Template l10n_cl para factura proveedor")
print("-" * 80)

# Buscar templates l10n_cl de factura
cl_templates = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[
        ['key', 'ilike', 'l10n_cl'],
        ['key', 'ilike', 'report_invoice'],
        ['type', '=', 'qweb']
    ]],
    {'fields': ['id', 'name', 'key', 'inherit_id'], 'order': 'key'}
)

print(f"\n✅ Templates l10n_cl de invoice: {len(cl_templates)}")
for t in cl_templates:
    print(f"  ID: {t['id']} | {t['key']}")

# ============================================================
# PASO 5: Verificar qué factura usa qué template
# ============================================================
print("\n" + "-" * 80)
print("PASO 5: Verificar _get_name_invoice_report de FAC 000849")
print("-" * 80)

# Obtener la factura
factura = models.execute_kw(db, uid, password,
    'account.move', 'search_read',
    [[['name', 'ilike', 'FAC 000849']]],
    {'fields': ['id', 'name', 'l10n_latam_document_type_id', 'company_id'], 'limit': 1}
)

if factura:
    f = factura[0]
    print(f"\n  Factura ID: {f['id']}")
    print(f"  Nombre: {f['name']}")
    print(f"  l10n_latam_document_type_id: {f.get('l10n_latam_document_type_id')}")
    print(f"  company_id: {f.get('company_id')}")
    
    # Verificar si tiene método _get_name_invoice_report
    try:
        report_name = models.execute_kw(db, uid, password,
            'account.move', '_get_name_invoice_report',
            [[f['id']]]
        )
        print(f"  Template usado: {report_name}")
    except Exception as e:
        print(f"  ⚠️  No se puede llamar _get_name_invoice_report via RPC")
        print(f"     El template se determina en runtime basado en l10n")

print("\n" + "=" * 100)
print("FIN INVESTIGACIÓN")
print("=" * 100)
