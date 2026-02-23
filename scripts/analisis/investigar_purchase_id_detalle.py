"""
FASE 1 - Investigación ADICIONAL: Analizar purchase_id en account.move
y evaluar comportamiento con múltiples OCs
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
print("INVESTIGACIÓN ADICIONAL: CAMPO purchase_id EN account.move")
print("=" * 100)

# ============================================================================
# ANÁLISIS 1: ¿Qué valor tiene purchase_id en facturas con múltiples OCs?
# ============================================================================
print("\n" + "=" * 100)
print("ANÁLISIS 1: ¿Qué valor tiene purchase_id en facturas con múltiples OCs?")
print("=" * 100)

# Buscar facturas con múltiples orígenes y revisar purchase_id
facturas_multi = models.execute_kw(db, uid, password,
    'account.move', 'search_read',
    [[
        ['move_type', '=', 'in_invoice'],
        ['invoice_origin', 'like', '%,%'],  # Múltiples orígenes
    ]],
    {
        'fields': ['id', 'name', 'invoice_origin', 'purchase_id', 'purchase_order_count'],
        'limit': 5,
        'order': 'create_date desc'
    }
)

print(f"\n📊 Facturas con múltiples OCs:")
for f in facturas_multi:
    print(f"\n  ID: {f['id']} | {f['name']}")
    print(f"    invoice_origin:       {f['invoice_origin'][:80]}...")
    print(f"    purchase_id:          {f['purchase_id']}")
    print(f"    purchase_order_count: {f['purchase_order_count']}")

# ============================================================================
# ANÁLISIS 2: Facturas con UNA sola OC - ¿purchase_id tiene valor?
# ============================================================================
print("\n" + "=" * 100)
print("ANÁLISIS 2: Facturas con UNA sola OC - ¿purchase_id tiene valor?")
print("=" * 100)

# Buscar facturas con un solo origen (sin comas)
facturas_single = models.execute_kw(db, uid, password,
    'account.move', 'search_read',
    [[
        ['move_type', '=', 'in_invoice'],
        ['invoice_origin', '!=', False],
        ['invoice_origin', 'not like', '%,%'],
        ['invoice_origin', 'like', 'OC%'],
    ]],
    {
        'fields': ['id', 'name', 'invoice_origin', 'purchase_id', 'purchase_order_count',
                   'invoice_date', 'date'],
        'limit': 5,
        'order': 'create_date desc'
    }
)

print(f"\n📊 Facturas con UNA sola OC:")
for f in facturas_single:
    print(f"\n  ID: {f['id']} | {f['name']}")
    print(f"    invoice_origin:       {f['invoice_origin']}")
    print(f"    purchase_id:          {f['purchase_id']}")
    print(f"    purchase_order_count: {f['purchase_order_count']}")
    print(f"    invoice_date:         {f['invoice_date']}")
    
    # Si tiene purchase_id, obtener la fecha de la OC
    if f['purchase_id']:
        po_id = f['purchase_id'][0]
        po = models.execute_kw(db, uid, password,
            'purchase.order', 'search_read',
            [[['id', '=', po_id]]],
            {'fields': ['id', 'name', 'date_order', 'date_approve']}
        )
        if po:
            print(f"    └─> OC date_order:   {po[0]['date_order']}")
            print(f"    └─> OC date_approve: {po[0]['date_approve']}")


# ============================================================================
# ANÁLISIS 3: Verificar atributos del campo purchase_id
# ============================================================================
print("\n" + "=" * 100)
print("ANÁLISIS 3: Atributos del campo purchase_id en account.move")
print("=" * 100)

move_fields = models.execute_kw(db, uid, password,
    'account.move', 'fields_get',
    [['purchase_id', 'purchase_order_count', 'invoice_origin']],
    {'attributes': ['string', 'type', 'relation', 'compute', 'store', 'readonly', 'help']}
)

for field, attrs in move_fields.items():
    print(f"\n📋 {field}:")
    for attr, value in attrs.items():
        if value:
            print(f"    {attr}: {value}")


# ============================================================================
# ANÁLISIS 4: Obtener todas las OCs únicas vinculadas a una factura multi-OC
# ============================================================================
print("\n" + "=" * 100)
print("ANÁLISIS 4: Obtener TODAS las OCs de una factura con múltiples orígenes")
print("=" * 100)

if facturas_multi:
    factura_test = facturas_multi[0]
    print(f"\nFactura ID: {factura_test['id']} ({factura_test['name']})")
    
    # Obtener TODAS las líneas con sus purchase_order_id
    lineas = models.execute_kw(db, uid, password,
        'account.move.line', 'search_read',
        [[
            ['move_id', '=', factura_test['id']], 
            ['display_type', 'not in', ['line_section', 'line_note', 'line_subtotal']],
            ['purchase_order_id', '!=', False]
        ]],
        {
            'fields': ['id', 'purchase_order_id', 'purchase_line_id'],
            'limit': 100
        }
    )
    
    # Extraer IDs únicos de OCs
    unique_po_ids = set()
    for linea in lineas:
        if linea.get('purchase_order_id'):
            po_id = linea['purchase_order_id'][0]
            unique_po_ids.add(po_id)
    
    print(f"\n✅ OCs únicas encontradas via invoice_line_ids: {len(unique_po_ids)}")
    
    # Obtener detalles de cada OC
    if unique_po_ids:
        ordenes = models.execute_kw(db, uid, password,
            'purchase.order', 'search_read',
            [[['id', 'in', list(unique_po_ids)]]],
            {
                'fields': ['id', 'name', 'date_order', 'date_approve'],
                'order': 'date_order asc'
            }
        )
        
        print("\n📦 Fechas de las OCs vinculadas (ordenadas por date_order):")
        fechas_oc = []
        for o in ordenes:
            fecha = o['date_order'][:10] if o['date_order'] else 'N/A'
            fechas_oc.append(fecha)
            print(f"    {o['name']:15} | date_order: {o['date_order']}")
        
        # Análisis de fechas
        print(f"\n📊 RESUMEN DE FECHAS:")
        print(f"    Fecha más antigua: {min(fechas_oc)}")
        print(f"    Fecha más reciente: {max(fechas_oc)}")
        print(f"    ¿Todas iguales?: {len(set(fechas_oc)) == 1}")


# ============================================================================
# ANÁLISIS 5: ¿Existe campo computado para esto ya?
# ============================================================================
print("\n" + "=" * 100)
print("ANÁLISIS 5: Buscar campos computados relacionados con fecha OC")
print("=" * 100)

# Buscar todos los campos x_studio que podrían estar relacionados
all_fields = models.execute_kw(db, uid, password,
    'account.move', 'fields_get',
    [],
    {'attributes': ['string', 'type', 'compute', 'store']}
)

# Filtrar por fecha o date
fecha_fields = {k: v for k, v in all_fields.items() 
                if ('fecha' in k.lower() or 'date' in k.lower()) 
                and k.startswith('x_')}

print(f"\n📋 Campos personalizados con 'fecha' o 'date' en account.move:")
for field, attrs in sorted(fecha_fields.items()):
    compute = "COMPUTADO" if attrs.get('compute') else ""
    stored = "STORED" if attrs.get('store') else ""
    print(f"    {field:45} | {attrs.get('string', '-'):30} | {attrs.get('type'):10} | {compute} {stored}")


# ============================================================================
# ANÁLISIS 6: Probar acceso via related field
# ============================================================================
print("\n" + "=" * 100)
print("ANÁLISIS 6: Probar acceso directo purchase_id.date_order")
print("=" * 100)

if facturas_single:
    factura_con_po = next((f for f in facturas_single if f['purchase_id']), None)
    if factura_con_po:
        print(f"\nFactura: {factura_con_po['name']} con purchase_id: {factura_con_po['purchase_id']}")
        
        # Intentar leer campos relacionados
        try:
            factura_detail = models.execute_kw(db, uid, password,
                'account.move', 'read',
                [[factura_con_po['id']]],
                {'fields': ['purchase_id']}
            )
            
            # Obtener la OC directamente
            if factura_detail and factura_detail[0]['purchase_id']:
                po_id = factura_detail[0]['purchase_id'][0]
                po = models.execute_kw(db, uid, password,
                    'purchase.order', 'read',
                    [[po_id]],
                    {'fields': ['date_order', 'date_approve', 'name']}
                )
                print(f"\n✅ Acceso exitoso via purchase_id:")
                print(f"    purchase_id.name: {po[0]['name']}")
                print(f"    purchase_id.date_order: {po[0]['date_order']}")
                print(f"    purchase_id.date_approve: {po[0]['date_approve']}")
        except Exception as e:
            print(f"❌ Error: {e}")


print("\n" + "=" * 100)
print("RESUMEN TÉCNICO")
print("=" * 100)
print("""
HALLAZGOS CLAVE:

1. MODELO: Las facturas de proveedor son account.move con move_type='in_invoice'

2. VINCULACIÓN:
   - account.move tiene campo 'purchase_id' (many2one a purchase.order)
   - account.move.line tiene campo 'purchase_order_id' (many2one a purchase.order)
   - account.move.line tiene campo 'purchase_line_id' (many2one a purchase.order.line)

3. COMPORTAMIENTO CON MÚLTIPLES OCs:
   - purchase_id en account.move apunta a UNA SOLA OC (o False)
   - Para facturas con múltiples OCs, se debe recorrer invoice_line_ids

4. FECHAS:
   - purchase.order.date_order = Fecha de creación de la OC
   - purchase.order.date_approve = Fecha de aprobación
   - purchase.order.line.date_planned = Fecha planificada de entrega
""")
