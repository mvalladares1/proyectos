"""
DEBUG: Analizar factura borrador y sus apuntes contables
OBJETIVO: Entender cómo Odoo convierte USD a CLP
- ¿Usa tipo de cambio de la OC o uno general?
- ¿Aplica sobre monto con IVA o sin IVA?
- ¿Cómo se relacionan líneas de factura con apuntes contables?
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
print("ANÁLISIS COMPLETO: CONVERSIÓN USD → CLP EN FACTURAS")
print("=" * 100)

# Buscar factura borrador FAC 000001 o similar
print("\n🔍 Buscando facturas de proveedor en borrador...")

facturas = models.execute_kw(db, uid, password,
    'account.move', 'search_read',
    [[['move_type', '=', 'in_invoice'],
      ['state', '=', 'draft']]],
    {'fields': ['id', 'name', 'partner_id', 'invoice_date', 'currency_id', 
                'amount_total', 'amount_untaxed', 'amount_tax',
                'amount_total_signed', 'amount_untaxed_signed',
                'invoice_origin', 'invoice_line_ids', 'line_ids'],
     'limit': 5,
     'order': 'id desc'}
)

print(f"\n✅ Encontradas {len(facturas)} facturas en borrador")

for idx, fac in enumerate(facturas[:2], 1):
    print(f"\n" + "=" * 100)
    print(f"FACTURA #{idx}: {fac.get('name', 'Sin nombre')}")
    print("=" * 100)
    
    moneda = fac.get('currency_id', ['N/A', 'N/A'])
    moneda_name = moneda[1] if isinstance(moneda, list) else moneda
    
    print(f"\n📌 DATOS GENERALES:")
    print(f"   ID: {fac['id']}")
    print(f"   Proveedor: {fac.get('partner_id', 'N/A')}")
    print(f"   Moneda documento: {moneda_name}")
    
    print(f"\n💵 MONTOS EN MONEDA DOCUMENTO ({moneda_name}):")
    print(f"   Base imponible (sin IVA): {fac.get('amount_untaxed', 0):,.2f}")
    print(f"   IVA:                      {fac.get('amount_tax', 0):,.2f}")
    print(f"   TOTAL (con IVA):          {fac.get('amount_total', 0):,.2f}")
    
    print(f"\n💰 MONTOS SIGNED (¿En CLP?):")
    print(f"   Untaxed Signed: {fac.get('amount_untaxed_signed', 0):,.2f}")
    print(f"   Total Signed:   {fac.get('amount_total_signed', 0):,.2f}")
    
    # Calcular tipo de cambio implícito
    if fac.get('amount_total', 0) > 0 and fac.get('amount_total_signed', 0) > 0:
        tc_total = abs(fac.get('amount_total_signed', 0)) / fac.get('amount_total', 0)
        tc_untaxed = abs(fac.get('amount_untaxed_signed', 0)) / fac.get('amount_untaxed', 0) if fac.get('amount_untaxed', 0) > 0 else 0
        print(f"\n📊 TIPO DE CAMBIO IMPLÍCITO:")
        print(f"   TC (Total):   {tc_total:,.4f}")
        print(f"   TC (Untaxed): {tc_untaxed:,.4f}")
    
    # Leer líneas de factura detalladas
    invoice_line_ids = fac.get('invoice_line_ids', [])
    if invoice_line_ids:
        print(f"\n" + "-" * 80)
        print(f"📋 LÍNEAS DE FACTURA ({len(invoice_line_ids)} líneas)")
        print("-" * 80)
        
        lines = models.execute_kw(db, uid, password,
            'account.move.line', 'read',
            [invoice_line_ids],
            {'fields': ['id', 'name', 'product_id', 'quantity', 'price_unit', 
                        'price_subtotal', 'price_total', 'currency_id',
                        'balance', 'amount_currency', 'debit', 'credit',
                        'tax_ids', 'account_id', 'display_type']}
        )
        
        for line in lines:
            if line.get('display_type') in ['line_section', 'line_note']:
                continue  # Saltar secciones y notas
                
            nombre = (line.get('name') or 'N/A')[:50]
            qty = line.get('quantity', 0)
            precio_usd = line.get('price_unit', 0)
            subtotal_usd = line.get('price_subtotal', 0)  # Sin IVA
            total_usd = line.get('price_total', 0)  # Con IVA
            balance_clp = line.get('balance', 0)
            amount_currency = line.get('amount_currency', 0)
            debit = line.get('debit', 0)
            credit = line.get('credit', 0)
            
            print(f"\n   📦 {nombre}")
            print(f"      Qty: {qty:,.2f}")
            print(f"      --- EN USD ---")
            print(f"      Precio Unit USD: {precio_usd:,.2f}")
            print(f"      Subtotal (sin IVA): USD {subtotal_usd:,.2f}")
            print(f"      Total (con IVA):    USD {total_usd:,.2f}")
            print(f"      --- EN CLP (apuntes) ---")
            print(f"      Debit:  CLP$ {debit:,.0f}")
            print(f"      Credit: CLP$ {credit:,.0f}")
            print(f"      Balance: CLP$ {balance_clp:,.0f}")
            print(f"      Amount Currency: {amount_currency:,.2f}")
            
            # Calcular TC de esta línea
            if subtotal_usd > 0 and debit > 0:
                tc_linea = debit / subtotal_usd
                print(f"      ⚡ TC implícito (debit/subtotal): {tc_linea:,.4f}")
    
    # Leer APUNTES CONTABLES completos
    line_ids = fac.get('line_ids', [])
    if line_ids:
        print(f"\n" + "-" * 80)
        print(f"📊 APUNTES CONTABLES ({len(line_ids)} líneas)")
        print("-" * 80)
        
        all_lines = models.execute_kw(db, uid, password,
            'account.move.line', 'read',
            [line_ids],
            {'fields': ['id', 'name', 'account_id', 'debit', 'credit', 
                        'balance', 'amount_currency', 'currency_id',
                        'product_id', 'quantity', 'price_unit', 'tax_line_id']}
        )
        
        total_debit = 0
        total_credit = 0
        
        for line in all_lines:
            cuenta = line.get('account_id', ['N/A', 'N/A'])
            cuenta_name = cuenta[1] if isinstance(cuenta, list) else str(cuenta)
            nombre = (line.get('name') or 'N/A')[:40]
            debit = line.get('debit', 0)
            credit = line.get('credit', 0)
            amount_currency = line.get('amount_currency', 0)
            es_iva = line.get('tax_line_id', False)
            
            total_debit += debit
            total_credit += credit
            
            if debit > 0 or credit > 0:
                tipo = "📌 IVA" if es_iva else "📦 Línea"
                print(f"\n   {tipo}: {nombre}")
                print(f"      Cuenta: {cuenta_name[:40]}")
                print(f"      Debit:  CLP$ {debit:>15,.0f}")
                print(f"      Credit: CLP$ {credit:>15,.0f}")
                print(f"      Monto moneda orig: {amount_currency:,.2f}")
                
                # Calcular TC
                if abs(amount_currency) > 0 and (debit > 0 or credit > 0):
                    monto_clp = debit if debit > 0 else credit
                    tc = monto_clp / abs(amount_currency)
                    print(f"      ⚡ TC: {tc:,.4f}")
        
        print(f"\n   {'=' * 50}")
        print(f"   TOTAL Debit:  CLP$ {total_debit:>15,.0f}")
        print(f"   TOTAL Credit: CLP$ {total_credit:>15,.0f}")

# Buscar OCs para comparar tipo de cambio
print("\n" + "=" * 100)
print("🔍 ÓRDENES DE COMPRA - TIPO DE CAMBIO")
print("=" * 100)

ocs = ['OC12641', 'OC12631', 'OC12567', 'OC12561', 'OC12527', 'OC12518', 'OC12285']

for oc_name in ocs:
    oc = models.execute_kw(db, uid, password,
        'purchase.order', 'search_read',
        [[['name', '=', oc_name]]],
        {'fields': ['id', 'name', 'currency_id', 'amount_total', 'amount_untaxed',
                    'date_order', 'x_studio_tipo_de_cambio', 'x_studio_monto_clp']}
    )
    
    if oc:
        o = oc[0]
        tc_oc = o.get('x_studio_tipo_de_cambio', 0) or 0
        monto_clp_oc = o.get('x_studio_monto_clp', 0) or 0
        monto_usd = o.get('amount_total', 0)
        monto_untaxed = o.get('amount_untaxed', 0)
        
        # Calcular TC implícito si hay monto CLP
        tc_calculado = monto_clp_oc / monto_usd if monto_usd > 0 and monto_clp_oc > 0 else 0
        
        print(f"\n   {o['name']}:")
        print(f"      Fecha: {o.get('date_order', 'N/A')[:10] if o.get('date_order') else 'N/A'}")
        print(f"      USD Total: {monto_usd:,.2f} | USD Base: {monto_untaxed:,.2f}")
        print(f"      TC guardado (x_studio): {tc_oc:,.4f}")
        print(f"      Monto CLP (x_studio):   {monto_clp_oc:,.0f}")
        if tc_calculado > 0:
            print(f"      TC calculado (CLP/USD): {tc_calculado:,.4f}")

# Buscar tipo de cambio del sistema
print("\n" + "=" * 100)
print("💱 TIPO DE CAMBIO DEL SISTEMA (res.currency.rate)")
print("=" * 100)

# Buscar USD
usd = models.execute_kw(db, uid, password,
    'res.currency', 'search_read',
    [[['name', '=', 'USD']]],
    {'fields': ['id', 'name', 'rate', 'symbol']}
)

if usd:
    usd_id = usd[0]['id']
    print(f"\n   USD ID: {usd_id}")
    print(f"   Rate actual: {usd[0].get('rate', 0)}")
    
    # Buscar historial de rates
    rates = models.execute_kw(db, uid, password,
        'res.currency.rate', 'search_read',
        [[['currency_id', '=', usd_id]]],
        {'fields': ['name', 'rate', 'inverse_company_rate', 'company_rate'],
         'limit': 10,
         'order': 'name desc'}
    )
    
    print(f"\n   Últimos 10 tipos de cambio USD:")
    for r in rates:
        fecha = r.get('name', 'N/A')
        rate = r.get('rate', 0)
        inverse = r.get('inverse_company_rate', 0)
        company = r.get('company_rate', 0)
        print(f"      {fecha}: rate={rate:.6f} | inverse={inverse:.2f} | company={company:.6f}")

print("\n" + "=" * 100)
print("📋 CONCLUSIONES")
print("=" * 100)
print("""
Para convertir USD → CLP en proformas:

1. OPCIÓN A: Usar tipo de cambio de la OC (x_studio_tipo_de_cambio)
   - Cada OC tiene su propio TC
   - Más preciso pero requiere leer cada OC

2. OPCIÓN B: Usar los apuntes contables que Odoo ya calculó
   - Odoo ya hizo la conversión en 'debit'/'credit'
   - Solo necesitamos leer esos valores

3. CAMPOS IMPORTANTES:
   - Factura: amount_untaxed (base), amount_tax (IVA), amount_total
   - Línea: price_subtotal (sin IVA), price_total (con IVA)
   - Apunte: debit/credit (en CLP), amount_currency (en USD)
""")

print("\n" + "=" * 100)
print("FIN DEL ANÁLISIS")
print("=" * 100)
