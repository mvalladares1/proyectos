#!/usr/bin/env python3
"""
Análisis de OC11681 - Cambio de moneda CLP a USD
"""
import xmlrpc.client
import ssl

# Configuración
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Buscar la OC por nombre
NOMBRE_OC = "OC11681"

print("="*80)
print(f"ANÁLISIS DE {NOMBRE_OC} - CAMBIO DE MONEDA CLP → USD")
print("="*80)

try:
    # Autenticación
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        raise Exception("❌ Error de autenticación")
    
    print("✅ Conectado\n")
    
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())
    
    # Buscar la OC
    oc_ids = models.execute_kw(db, uid, password,
        'purchase.order', 'search',
        [[('name', '=', NOMBRE_OC)]])
    
    if not oc_ids:
        print(f"❌ No se encontró la OC {NOMBRE_OC}")
        exit(1)
    
    oc_id = oc_ids[0]
    
    # Leer datos de la OC
    oc = models.execute_kw(db, uid, password,
        'purchase.order', 'read',
        [oc_id],
        {'fields': ['name', 'state', 'amount_total', 'currency_id', 'partner_id', 'invoice_status']})[0]
    
    print(f"📋 OC: {oc['name']} (ID: {oc_id})")
    print(f"📋 Estado: {oc['state']}")
    print(f"💰 Total: ${oc['amount_total']:,.2f} {oc['currency_id'][1]}")
    print(f"🏢 Proveedor: {oc['partner_id'][1]}")
    print(f"🧾 Facturación: {oc['invoice_status']}")
    
    # Obtener monedas
    currency_clp = models.execute_kw(db, uid, password,
        'res.currency', 'search',
        [[('name', '=', 'CLP')]])[0]
    
    currency_usd = models.execute_kw(db, uid, password,
        'res.currency', 'search',
        [[('name', '=', 'USD')]])[0]
    
    print(f"\n💱 Moneda actual: {oc['currency_id'][1]} (ID: {oc['currency_id'][0]})")
    print(f"💱 Moneda CLP ID: {currency_clp}")
    print(f"💱 Moneda USD ID: {currency_usd}")
    
    if oc['currency_id'][0] != currency_clp:
        print(f"\n⚠️  ADVERTENCIA: La OC no está en CLP, está en {oc['currency_id'][1]}")
    
    # Buscar líneas de la OC
    lineas = models.execute_kw(db, uid, password,
        'purchase.order.line', 'search_read',
        [[('order_id', '=', oc_id)]],
        {'fields': ['id', 'name', 'product_id', 'product_qty', 'price_unit', 'price_subtotal', 'currency_id']})
    
    print(f"\n📦 Líneas de compra ({len(lineas)}):")
    for linea in lineas:
        print(f"   • Línea {linea['id']}: {linea['product_id'][1] if linea['product_id'] else 'Sin producto'}")
        print(f"     Cantidad: {linea['product_qty']}, Precio: ${linea['price_unit']:,.2f}, Subtotal: ${linea['price_subtotal']:,.2f}")
        print(f"     Moneda: {linea['currency_id'][1]} (ID: {linea['currency_id'][0]})")
    
    # Buscar movimientos de stock relacionados
    moves = models.execute_kw(db, uid, password,
        'stock.move', 'search_read',
        [[('purchase_line_id', 'in', [l['id'] for l in lineas])]],
        {'fields': ['id', 'name', 'product_id', 'product_qty', 'price_unit', 'purchase_line_id']})
    
    print(f"\n📦 Movimientos de stock ({len(moves)}):")
    for move in moves:
        print(f"   • Move {move['id']}: {move['product_id'][1] if move['product_id'] else 'Sin producto'}")
        print(f"     Cantidad: {move['product_qty']}, Precio: ${move['price_unit']:,.2f}")
        print(f"     Línea OC: {move['purchase_line_id'][0] if move['purchase_line_id'] else 'N/A'}")
    
    # Buscar capas de valoración
    layers = models.execute_kw(db, uid, password,
        'stock.valuation.layer', 'search_read',
        [[('stock_move_id', 'in', [m['id'] for m in moves])]],
        {'fields': ['id', 'product_id', 'quantity', 'unit_cost', 'value', 'currency_id', 'stock_move_id']})
    
    print(f"\n💰 Capas de valoración ({len(layers)}):")
    for layer in layers:
        print(f"   • Layer {layer['id']}: {layer['product_id'][1] if layer['product_id'] else 'Sin producto'}")
        print(f"     Cantidad: {layer['quantity']}, Costo: ${layer['unit_cost']:,.2f}, Valor: ${layer['value']:,.2f}")
        print(f"     Moneda: {layer['currency_id'][1]} (ID: {layer['currency_id'][0]})")
        print(f"     Move: {layer['stock_move_id'][0] if layer['stock_move_id'] else 'N/A'}")
    
    # Verificar facturas
    facturas = models.execute_kw(db, uid, password,
        'account.move', 'search_read',
        [[('invoice_origin', '=', NOMBRE_OC)]],
        {'fields': ['id', 'name', 'state', 'move_type', 'amount_total', 'currency_id']})
    
    print(f"\n🧾 Facturas relacionadas ({len(facturas)}):")
    if facturas:
        for factura in facturas:
            print(f"   • Factura {factura['name']} (ID: {factura['id']}): {factura['state']}")
            print(f"     Tipo: {factura['move_type']}, Total: ${factura['amount_total']:,.2f} {factura['currency_id'][1]}")
    else:
        print("   ✓ No hay facturas relacionadas")
    
    print("\n" + "="*80)
    print("RESUMEN PARA CORRECCIÓN")
    print("="*80)
    print(f"OC ID: {oc_id}")
    print(f"Moneda actual: {oc['currency_id'][1]} (ID: {oc['currency_id'][0]})")
    print(f"Cambiar a: USD (ID: {currency_usd})")
    print(f"Total líneas: {len(lineas)}")
    print(f"Total moves: {len(moves)}")
    print(f"Total layers: {len(layers)}")
    print(f"Total facturas: {len(facturas)}")
    
    if facturas:
        print("\n⚠️  HAY FACTURAS - Se deben eliminar las borrador antes de cambiar moneda")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
