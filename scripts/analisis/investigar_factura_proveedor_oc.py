"""
FASE 1 - Investigación: Relación Factura Proveedor <-> Orden de Compra
Objetivo: Determinar cómo obtener correctamente la "Fecha de OC" (purchase.order.date_order)
"""
import xmlrpc.client
from datetime import datetime

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
print("FASE 1 - INVESTIGACIÓN: FACTURA PROVEEDOR <-> ORDEN DE COMPRA")
print("=" * 100)

# ============================================================================
# PASO 1: Identificar el modelo exacto del documento (account.move)
# ============================================================================
print("\n" + "=" * 100)
print("PASO 1: IDENTIFICAR MODELO FACTURA PROVEEDOR (account.move)")
print("=" * 100)

# Buscar facturas de proveedor recientes que tengan origen de OC
facturas = models.execute_kw(db, uid, password,
    'account.move', 'search_read',
    [[
        ['move_type', '=', 'in_invoice'],  # Factura de proveedor
        ['invoice_origin', '!=', False],    # Con origen (puede venir de OC)
        ['state', 'in', ['draft', 'posted']],
    ]],
    {
        'fields': ['id', 'name', 'move_type', 'invoice_date', 'date', 
                   'invoice_origin', 'ref', 'state', 'partner_id',
                   'invoice_line_ids', 'create_date'],
        'limit': 5,
        'order': 'create_date desc'
    }
)

print(f"\n✅ Encontradas {len(facturas)} facturas de proveedor con origen")

if facturas:
    for idx, factura in enumerate(facturas):
        print(f"\n{'─' * 80}")
        print(f"FACTURA #{idx+1}")
        print(f"{'─' * 80}")
        print(f"  ID:              {factura['id']}")
        print(f"  Nombre:          {factura['name']}")
        print(f"  move_type:       {factura['move_type']}")
        print(f"  invoice_date:    {factura['invoice_date']}")
        print(f"  date:            {factura['date']}")
        print(f"  invoice_origin:  {factura['invoice_origin']}")
        print(f"  ref:             {factura['ref']}")
        print(f"  state:           {factura['state']}")
        print(f"  partner_id:      {factura['partner_id']}")
        print(f"  create_date:     {factura['create_date']}")
        print(f"  invoice_line_ids: {factura['invoice_line_ids'][:5]}...")  # Primeras 5


# ============================================================================
# PASO 2: Investigar vinculación con Orden de Compra
# ============================================================================
print("\n" + "=" * 100)
print("PASO 2: INVESTIGAR VINCULACIÓN invoice_line_ids -> purchase_line_id -> order_id")
print("=" * 100)

# Primero verificar si existe el campo purchase_line_id en account.move.line
print("\n📋 Verificando campos disponibles en account.move.line...")

# Obtener campos del modelo account.move.line
try:
    line_fields = models.execute_kw(db, uid, password,
        'account.move.line', 'fields_get',
        [],
        {'attributes': ['string', 'type', 'relation']}
    )
    
    # Buscar campos relacionados con purchase
    purchase_fields = {k: v for k, v in line_fields.items() if 'purchase' in k.lower()}
    print(f"\n✅ Campos relacionados con 'purchase' en account.move.line:")
    for field, attrs in purchase_fields.items():
        print(f"  {field:40} | tipo: {attrs.get('type'):15} | relación: {attrs.get('relation', '-')}")
        
except Exception as e:
    print(f"❌ Error obteniendo campos: {e}")

# Ahora investigar las líneas de factura de la primera factura encontrada
if facturas:
    factura_test = facturas[0]
    print(f"\n{'─' * 80}")
    print(f"ANALIZANDO LÍNEAS DE FACTURA ID: {factura_test['id']} ({factura_test['name']})")
    print(f"invoice_origin: {factura_test['invoice_origin']}")
    print(f"{'─' * 80}")
    
    # Obtener las líneas de factura con todos los campos de purchase
    lineas = models.execute_kw(db, uid, password,
        'account.move.line', 'search_read',
        [[['move_id', '=', factura_test['id']], ['display_type', 'not in', ['line_section', 'line_note']]]],
        {
            'fields': ['id', 'name', 'product_id', 'quantity', 'price_unit', 
                       'purchase_line_id', 'purchase_order_id'],
            'limit': 10
        }
    )
    
    print(f"\n✅ Líneas encontradas: {len(lineas)}")
    
    purchase_orders_ids = set()
    
    for linea in lineas:
        print(f"\n  Línea ID: {linea['id']}")
        print(f"    product_id:        {linea.get('product_id')}")
        print(f"    name:              {str(linea.get('name', ''))[:60]}...")
        print(f"    purchase_line_id:  {linea.get('purchase_line_id')}")
        print(f"    purchase_order_id: {linea.get('purchase_order_id')}")
        
        # Si existe purchase_line_id, obtener la orden
        if linea.get('purchase_line_id'):
            po_line_id = linea['purchase_line_id'][0] if isinstance(linea['purchase_line_id'], (list, tuple)) else linea['purchase_line_id']
            
            po_line = models.execute_kw(db, uid, password,
                'purchase.order.line', 'search_read',
                [[['id', '=', po_line_id]]],
                {'fields': ['id', 'order_id', 'date_planned', 'product_id']}
            )
            
            if po_line:
                order_id = po_line[0]['order_id'][0] if po_line[0].get('order_id') else None
                if order_id:
                    purchase_orders_ids.add(order_id)
                print(f"    └─> purchase.order.line.order_id: {po_line[0].get('order_id')}")
                print(f"    └─> purchase.order.line.date_planned: {po_line[0].get('date_planned')}")
    
    # ============================================================================
    # PASO 2.1: Obtener datos de las ÓRDENES DE COMPRA vinculadas
    # ============================================================================
    if purchase_orders_ids:
        print(f"\n{'─' * 80}")
        print(f"ÓRDENES DE COMPRA VINCULADAS: {list(purchase_orders_ids)}")
        print(f"{'─' * 80}")
        
        ordenes = models.execute_kw(db, uid, password,
            'purchase.order', 'search_read',
            [[['id', 'in', list(purchase_orders_ids)]]],
            {'fields': ['id', 'name', 'date_order', 'date_approve', 'state', 
                        'partner_id', 'amount_total', 'order_line']}
        )
        
        for orden in ordenes:
            print(f"\n  📦 ORDEN DE COMPRA")
            print(f"    id:           {orden['id']}")
            print(f"    name:         {orden['name']}")
            print(f"    date_order:   {orden['date_order']}")
            print(f"    date_approve: {orden['date_approve']}")
            print(f"    state:        {orden['state']}")
            print(f"    partner_id:   {orden['partner_id']}")
    else:
        print("\n⚠️  No se encontraron órdenes de compra vinculadas via purchase_line_id")
        print("    Intentando buscar OC por invoice_origin...")
        
        # Buscar OC por nombre en invoice_origin
        origin = factura_test.get('invoice_origin', '')
        if origin:
            # El origin puede tener formato "PO00123" o múltiples "PO00123, PO00124"
            oc_names = [name.strip() for name in origin.split(',')]
            print(f"    Buscando OCs con nombres: {oc_names}")
            
            ordenes_by_origin = models.execute_kw(db, uid, password,
                'purchase.order', 'search_read',
                [[['name', 'in', oc_names]]],
                {'fields': ['id', 'name', 'date_order', 'date_approve', 'state', 'partner_id']}
            )
            
            for orden in ordenes_by_origin:
                print(f"\n  📦 ORDEN DE COMPRA (por invoice_origin)")
                print(f"    id:           {orden['id']}")
                print(f"    name:         {orden['name']}")
                print(f"    date_order:   {orden['date_order']}")
                print(f"    date_approve: {orden['date_approve']}")
                print(f"    state:        {orden['state']}")


# ============================================================================
# PASO 3: Evaluar todas las fechas disponibles
# ============================================================================
print("\n" + "=" * 100)
print("PASO 3: EVALUAR TODAS LAS FECHAS DISPONIBLES")
print("=" * 100)

print("""
📅 RESUMEN DE FECHAS DISPONIBLES:

1. account.move.invoice_date
   - Fecha de la factura del proveedor
   - Es la fecha que aparece en el documento fiscal
   - Puede ser diferente a la fecha de la OC

2. account.move.date
   - Fecha contable del asiento
   - Usada para efectos contables/fiscales
   
3. purchase.order.date_order
   - Fecha de CREACIÓN de la orden de compra
   - Esta es típicamente la "Fecha de OC" que se busca
   - Es la fecha en que se generó la solicitud de compra
   
4. purchase.order.date_approve
   - Fecha en que la OC fue APROBADA/CONFIRMADA
   - Puede ser diferente a date_order si hay flujo de aprobación
   - Puede ser NULL si la OC está en borrador
   
5. purchase.order.line.date_planned
   - Fecha planificada de RECEPCIÓN del producto
   - Es por línea de producto
   - Usada para logística/planificación
""")


# ============================================================================
# PASO 4: Verificar campos existentes en account.move relacionados con purchase
# ============================================================================
print("\n" + "=" * 100)
print("PASO 4: VERIFICAR CAMPOS EXISTENTES EN account.move RELACIONADOS CON PURCHASE")
print("=" * 100)

move_fields = models.execute_kw(db, uid, password,
    'account.move', 'fields_get',
    [],
    {'attributes': ['string', 'type', 'relation', 'compute']}
)

purchase_move_fields = {k: v for k, v in move_fields.items() 
                        if 'purchase' in k.lower() or 'order' in k.lower()}

print("\n📋 Campos en account.move relacionados con 'purchase' u 'order':")
for field, attrs in sorted(purchase_move_fields.items()):
    compute_info = "computado" if attrs.get('compute') else ""
    print(f"  {field:40} | {attrs.get('string', '-'):30} | {attrs.get('type'):10} | {compute_info}")

# Buscar campos x_studio relacionados
x_studio_fields = {k: v for k, v in move_fields.items() if k.startswith('x_')}
if x_studio_fields:
    print(f"\n📋 Campos personalizados (x_studio) en account.move: ({len(x_studio_fields)} campos)")
    for field, attrs in sorted(x_studio_fields.items()):
        if 'fecha' in field.lower() or 'date' in field.lower() or 'order' in field.lower():
            print(f"  {field:40} | {attrs.get('string', '-'):30} | {attrs.get('type')}")


# ============================================================================
# ANÁLISIS ADICIONAL: Múltiples OCs por factura
# ============================================================================
print("\n" + "=" * 100)
print("ANÁLISIS ADICIONAL: BUSCAR FACTURAS CON MÚLTIPLES ÓRDENES DE COMPRA")
print("=" * 100)

# Buscar facturas donde invoice_origin tenga comas (múltiples OCs)
facturas_multi = models.execute_kw(db, uid, password,
    'account.move', 'search_read',
    [[
        ['move_type', '=', 'in_invoice'],
        ['invoice_origin', 'like', '%,%'],  # Contiene coma = múltiples orígenes
    ]],
    {
        'fields': ['id', 'name', 'invoice_origin', 'invoice_date'],
        'limit': 5,
        'order': 'create_date desc'
    }
)

print(f"\n📊 Facturas con múltiples orígenes (posibles múltiples OCs): {len(facturas_multi)}")
for f in facturas_multi:
    print(f"  ID: {f['id']:6} | {f['name']:20} | origen: {f['invoice_origin']}")


# ============================================================================
# VERIFICAR CASO ESPECÍFICO: Factura parcial de OC
# ============================================================================
print("\n" + "=" * 100)
print("ANÁLISIS: VERIFICAR SI EXISTEN FACTURAS PARCIALES DE OC")
print("=" * 100)

# Buscar una OC con múltiples facturas
if facturas:
    factura_test = facturas[0]
    origin = factura_test.get('invoice_origin', '')
    
    if origin:
        oc_name = origin.split(',')[0].strip()
        
        # Buscar todas las facturas con este origen
        facturas_misma_oc = models.execute_kw(db, uid, password,
            'account.move', 'search_read',
            [[
                ['move_type', '=', 'in_invoice'],
                ['invoice_origin', 'like', f'%{oc_name}%'],
            ]],
            {
                'fields': ['id', 'name', 'invoice_origin', 'invoice_date', 'state', 'amount_total'],
                'limit': 10
            }
        )
        
        print(f"\n📊 Facturas vinculadas a OC '{oc_name}': {len(facturas_misma_oc)}")
        for f in facturas_misma_oc:
            print(f"  ID: {f['id']:6} | {f.get('name', '-'):20} | {f.get('invoice_date', '-'):12} | {f.get('state'):10} | ${f.get('amount_total', 0):,.0f}")

print("\n" + "=" * 100)
print("FIN FASE 1 - INVESTIGACIÓN COMPLETADA")
print("=" * 100)
