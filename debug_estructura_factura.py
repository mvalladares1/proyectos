"""
Debug script para explorar la estructura completa de una factura y sus líneas.
Esto ayuda a entender cómo se organizan los datos en Odoo.
"""
import xmlrpc.client
import getpass
import json

ODOO_URL = "https://riofuturo.server98c6e.oerpondemand.net"
ODOO_DB = "riofuturo-master"

def main():
    print("=" * 100)
    print("DEBUG: Exploración de estructura de factura")
    print("=" * 100)
    
    email = input("Email Odoo: ")
    api_key = getpass.getpass("API Key: ")
    
    print("\n🔄 Conectando a Odoo...")
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, email, api_key, {})
    
    if not uid:
        print("❌ Error de autenticación")
        return
    
    print(f"✅ Conectado como UID: {uid}")
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    
    def search_read(model, domain, fields, limit=100):
        return models.execute_kw(ODOO_DB, uid, api_key, model, 'search_read', [domain], {'fields': fields, 'limit': limit})
    
    def fields_get(model):
        return models.execute_kw(ODOO_DB, uid, api_key, model, 'fields_get', [], {'attributes': ['string', 'type', 'relation']})
    
    # =========================================================================
    # PASO 1: Obtener campos disponibles en account.move.line
    # =========================================================================
    print("\n--- PASO 1: Campos disponibles en account.move.line ---")
    
    line_fields = fields_get('account.move.line')
    
    # Filtrar campos relevantes
    campos_relevantes = ['name', 'account_id', 'price_subtotal', 'price_total', 'debit', 'credit', 
                         'balance', 'quantity', 'price_unit', 'product_id', 'partner_id', 
                         'display_type', 'move_id', 'analytic_account_id', 'analytic_distribution']
    
    print("\nCampos existentes:")
    for campo in campos_relevantes:
        if campo in line_fields:
            info = line_fields[campo]
            print(f"  ✅ {campo}: {info.get('string')} ({info.get('type')})")
        else:
            print(f"  ❌ {campo}: NO EXISTE")
    
    # Buscar campos analytic_* disponibles
    print("\nCampos analytic* disponibles:")
    for campo, info in line_fields.items():
        if 'analytic' in campo.lower():
            print(f"  🔍 {campo}: {info.get('string')} ({info.get('type')})")
    
    # =========================================================================
    # PASO 2: Obtener una factura de ejemplo (en el rango futuro)
    # =========================================================================
    print("\n--- PASO 2: Factura de ejemplo ---")
    
    # Buscar un draft invoice de BCI
    moves = search_read(
        'account.move',
        [
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'draft'),
            ('partner_id', 'ilike', 'BCI'),
            ('invoice_date', '>=', '2026-11-01')
        ],
        ['id', 'name', 'partner_id', 'invoice_date', 'invoice_date_due', 'amount_total', 
         'amount_residual', 'state', 'move_type', 'x_studio_fecha_de_pago'],
        limit=1
    )
    
    if not moves:
        print("No se encontraron facturas de BCI. Buscando cualquier draft...")
        moves = search_read(
            'account.move',
            [
                ('move_type', 'in', ['in_invoice']),
                ('state', '=', 'draft'),
                ('invoice_date', '>=', '2026-11-01')
            ],
            ['id', 'name', 'partner_id', 'invoice_date', 'invoice_date_due', 'amount_total', 
             'amount_residual', 'state', 'move_type', 'x_studio_fecha_de_pago'],
            limit=1
        )
    
    if not moves:
        print("❌ No se encontraron facturas draft recientes")
        return
    
    move = moves[0]
    print(f"\n📄 FACTURA: {move.get('name', 'Sin nombre')}")
    print(f"   ID: {move['id']}")
    print(f"   Partner: {move['partner_id'][1] if move['partner_id'] else 'N/A'}")
    print(f"   Tipo: {move['move_type']}")
    print(f"   Estado: {move['state']}")
    print(f"   Fecha Factura: {move.get('invoice_date')}")
    print(f"   Fecha Vencimiento: {move.get('invoice_date_due')}")
    print(f"   x_studio_fecha_de_pago: {move.get('x_studio_fecha_de_pago')}")
    print(f"   Monto Total: ${move.get('amount_total', 0):,.0f}")
    print(f"   Monto Residual: ${move.get('amount_residual', 0):,.0f}")
    
    # =========================================================================
    # PASO 3: Obtener líneas de esta factura
    # =========================================================================
    print("\n--- PASO 3: Líneas de la factura ---")
    
    # Probar con diferentes filtros de display_type
    lines = search_read(
        'account.move.line',
        [('move_id', '=', move['id'])],
        ['name', 'account_id', 'price_subtotal', 'price_total', 'debit', 'credit', 
         'balance', 'quantity', 'price_unit', 'product_id', 'display_type', 
         'analytic_distribution'],
        limit=50
    )
    
    print(f"\nTotal líneas: {len(lines)}")
    
    # Agrupar por display_type
    by_type = {}
    for l in lines:
        dt = l.get('display_type') or 'product'
        by_type.setdefault(dt, []).append(l)
    
    print("\nLíneas por display_type:")
    for dt, items in by_type.items():
        print(f"  {dt}: {len(items)} líneas")
    
    # Mostrar líneas que NO son section/note (las que nos importan)
    print("\n📋 LÍNEAS DE PRODUCTO/SERVICIO (display_type != section/note):")
    total_subtotal = 0
    for l in lines:
        dt = l.get('display_type')
        if dt in ['line_section', 'line_note']:
            continue
            
        acc = l.get('account_id')
        acc_str = f"{acc[0]} - {acc[1]}" if acc else "N/A"
        subtotal = l.get('price_subtotal', 0)
        total_subtotal += subtotal
        
        print(f"\n  📦 {l.get('name', 'Sin nombre')[:60]}")
        print(f"     Cuenta: {acc_str}")
        print(f"     Subtotal: ${subtotal:,.0f}")
        print(f"     Débito: ${l.get('debit', 0):,.0f} | Crédito: ${l.get('credit', 0):,.0f}")
        print(f"     Balance: ${l.get('balance', 0):,.0f}")
        print(f"     display_type: {dt}")
        if l.get('analytic_distribution'):
            print(f"     Distribución Analítica: {l['analytic_distribution']}")
    
    print(f"\n📊 SUMA SUBTOTALES: ${total_subtotal:,.0f}")
    print(f"📊 AMOUNT_TOTAL: ${move.get('amount_total', 0):,.0f}")
    
    # =========================================================================
    # PASO 4: Entender la lógica de clasificación
    # =========================================================================
    print("\n--- PASO 4: Códigos de cuenta encontrados ---")
    
    account_ids = list(set(
        l['account_id'][0] for l in lines if l.get('account_id') and l.get('display_type') not in ['line_section', 'line_note']
    ))
    
    if account_ids:
        accs = search_read('account.account', [('id', 'in', account_ids)], ['code', 'name'], limit=50)
        
        print("\nCuentas usadas en esta factura:")
        for a in accs:
            print(f"  {a['code']} - {a['name']}")
    
    print("\n" + "=" * 100)
    print("DEBUG COMPLETADO")
    print("=" * 100)

if __name__ == "__main__":
    main()
