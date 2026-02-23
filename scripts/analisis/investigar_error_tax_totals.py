"""
Investigar y corregir error en template account.document_tax_totals_copy_3
Error: 'bool' object is not subscriptable - tax_totals es False
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
print("INVESTIGAR ERROR: account.document_tax_totals_copy_3")
print("=" * 100)

# ============================================================
# PASO 1: Buscar el template problemático
# ============================================================
print("\n" + "-" * 80)
print("PASO 1: Buscar template account.document_tax_totals_copy_3")
print("-" * 80)

templates = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[['key', 'ilike', 'document_tax_totals']]],
    {'fields': ['id', 'name', 'key', 'inherit_id', 'active', 'arch_db'], 'order': 'key'}
)

print(f"\n✅ Templates encontrados: {len(templates)}")
for t in templates:
    print(f"\n  ID: {t['id']}")
    print(f"  name: {t['name']}")
    print(f"  key: {t.get('key', '-')}")
    print(f"  inherit_id: {t.get('inherit_id', '-')}")
    print(f"  active: {t.get('active', True)}")

# ============================================================
# PASO 2: Ver el contenido del template con error
# ============================================================
print("\n" + "-" * 80)
print("PASO 2: Contenido del template con error")
print("-" * 80)

problem_template = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[['key', '=', 'account.document_tax_totals_copy_3']]],
    {'fields': ['id', 'name', 'key', 'arch_db', 'inherit_id']}
)

if problem_template:
    t = problem_template[0]
    print(f"\n  ID: {t['id']}")
    print(f"  key: {t['key']}")
    print(f"  inherit_id: {t.get('inherit_id')}")
    
    arch = t.get('arch_db', '')
    if arch:
        # Guardar para análisis
        with open('template_tax_totals_copy_3.xml', 'w', encoding='utf-8') as f:
            f.write(arch)
        print(f"\n📄 Guardado en: template_tax_totals_copy_3.xml")
        
        # Mostrar la línea problemática
        print("\n📋 Contenido:")
        print(arch[:2000])
else:
    print("❌ No se encontró el template")

# ============================================================
# PASO 3: Comparar con el template original
# ============================================================
print("\n" + "-" * 80)
print("PASO 3: Template original account.document_tax_totals")
print("-" * 80)

original_template = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[['key', '=', 'account.document_tax_totals']]],
    {'fields': ['id', 'name', 'key', 'arch_db']}
)

if original_template:
    t = original_template[0]
    print(f"\n  ID: {t['id']}")
    print(f"  key: {t['key']}")
    
    arch = t.get('arch_db', '')
    if arch:
        with open('template_tax_totals_original.xml', 'w', encoding='utf-8') as f:
            f.write(arch)
        print(f"\n📄 Guardado en: template_tax_totals_original.xml")
        
        # Ver si tiene validación de tax_totals
        if 't-if="tax_totals"' in arch or "t-if='tax_totals'" in arch:
            print("✅ Template original TIENE validación de tax_totals")
        else:
            print("⚠️  Template original NO tiene validación de tax_totals")

# ============================================================
# PASO 4: Verificar qué reportes usan este template
# ============================================================
print("\n" + "-" * 80)
print("PASO 4: ¿Qué reportes usan account.document_tax_totals_copy_3?")
print("-" * 80)

# Buscar vistas que referencien este template
views_using = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[['arch_db', 'ilike', 'document_tax_totals_copy_3']]],
    {'fields': ['id', 'name', 'key'], 'limit': 20}
)

print(f"\n📊 Vistas que usan document_tax_totals_copy_3: {len(views_using)}")
for v in views_using:
    print(f"  ID: {v['id']} | {v.get('key', v['name'])}")


# ============================================================
# PROPUESTA DE CORRECCIÓN
# ============================================================
print("\n" + "=" * 100)
print("PROPUESTA DE CORRECCIÓN")
print("=" * 100)

print("""
El error ocurre porque el template intenta iterar sobre tax_totals['subtotals']
pero tax_totals es False (boolean) en lugar de un diccionario.

SOLUCIÓN: Agregar validación t-if antes del foreach:

ORIGINAL (con error):
    <t t-foreach="tax_totals['subtotals']" t-as="subtotal"/>

CORREGIDO:
    <t t-if="tax_totals">
        <t t-foreach="tax_totals['subtotals']" t-as="subtotal"/>
    </t>

O bien, desactivar el template copy_3 y usar el original.
""")

# Preguntar si corregir
print("\n¿Desea aplicar la corrección? (requiere editar el template)")
