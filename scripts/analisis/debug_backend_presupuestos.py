"""
Debug: Simular la Query C del backend para presupuestos
"""
import xmlrpc.client
import sys

url = "http://167.114.114.51:8069"
db = "riofuturo"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

fecha_inicio = "2026-01-01"
fecha_fin = "2026-09-30"

print("="*80)
print("SIMULACIÓN DE QUERY C - PRESUPUESTOS DE VENTA")
print("="*80)
print(f"Rango: {fecha_inicio} a {fecha_fin}")
print()

try:
    # Autenticar
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("❌ Error de autenticación")
        sys.exit(1)
    
    print(f"✅ Autenticado como UID: {uid}\n")
    
    # Conectar a modelos
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    # EXACTAMENTE la misma query que el backend
    print("Ejecutando query exacta del backend...")
    print("Dominio: [")
    print("  ('state', 'in', ['draft', 'sent']),")
    print(f"  ('commitment_date', '>=', '{fecha_inicio}'),")
    print(f"  ('commitment_date', '<=', '{fecha_fin}')")
    print("]\n")
    
    presupuestos = models.execute_kw(
        db, uid, password,
        'sale.order', 'search_read',
        [[
            ('state', 'in', ['draft', 'sent']),
            ('commitment_date', '>=', fecha_inicio),
            ('commitment_date', '<=', fecha_fin)
        ]],
        {'fields': ['name', 'partner_id', 'amount_total', 'currency_id', 'commitment_date', 'date_order', 'state']}
    )
    
    print(f"📊 RESULTADO: {len(presupuestos)} presupuestos encontrados\n")
    
    if len(presupuestos) == 0:
        print("❌ NO SE ENCONTRARON PRESUPUESTOS")
        print("\nPosibles causas:")
        print("1. No hay presupuestos con state='draft' o 'sent' en ese rango")
        print("2. Los presupuestos no tienen commitment_date definido")
        print("3. Los presupuestos están en otro rango de fechas")
        
        # Verificar sin filtro de fecha
        print("\n" + "-"*80)
        print("Verificando presupuestos SIN filtro de fecha...")
        todos = models.execute_kw(
            db, uid, password,
            'sale.order', 'search_read',
            [[('state', 'in', ['draft', 'sent'])]],
            {'fields': ['name', 'commitment_date', 'amount_total', 'currency_id'], 'limit': 10}
        )
        
        print(f"Total presupuestos draft/sent (sin filtro fecha): {len(todos)}")
        if len(todos) > 0:
            print("\nPrimeros 10 presupuestos:")
            for p in todos[:10]:
                fecha = p.get('commitment_date', 'SIN FECHA')
                amount = p.get('amount_total', 0)
                currency = p.get('currency_id', [0, 'N/A'])[1] if p.get('currency_id') else 'N/A'
                print(f"  {p['name']:20s} | Fecha compromiso: {fecha} | {currency} ${amount:>12,.0f}")
    else:
        print("✅ PRESUPUESTOS ENCONTRADOS:\n")
        
        total_usd = 0
        total_clp = 0
        por_mes = {}
        
        for p in presupuestos:
            nombre = p.get('name', 'N/A')
            partner = p.get('partner_id', [0, 'N/A'])[1] if p.get('partner_id') else 'N/A'
            amount = p.get('amount_total', 0)
            currency = p.get('currency_id', [0, 'N/A'])[1] if p.get('currency_id') else 'N/A'
            fecha = p.get('commitment_date', 'N/A')
            state = p.get('state', 'N/A')
            
            mes = fecha[:7] if fecha and fecha != 'N/A' else 'SIN MES'
            
            if mes not in por_mes:
                por_mes[mes] = {'count': 0, 'total': 0}
            por_mes[mes]['count'] += 1
            por_mes[mes]['total'] += amount
            
            if 'USD' in currency.upper():
                total_usd += amount
            else:
                total_clp += amount
            
            print(f"{nombre:20s} | {partner[:30]:30s} | {currency:5s} ${amount:>12,.0f} | {fecha} | {state}")
        
        print("\n" + "="*80)
        print("RESUMEN:")
        print("="*80)
        print(f"Total USD: ${total_usd:,.2f}")
        print(f"Total CLP: ${total_clp:,.0f}")
        
        # Conversión estimada
        tasa_cambio = 950
        total_clp_convertido = total_clp + (total_usd * tasa_cambio)
        print(f"\nTotal en CLP (USD @ {tasa_cambio}): ${total_clp_convertido:,.0f}")
        
        print("\n" + "-"*80)
        print("DISTRIBUCIÓN POR MES:")
        print("-"*80)
        for mes in sorted(por_mes.keys()):
            data = por_mes[mes]
            print(f"{mes}: {data['count']:3d} presupuestos | ${data['total']:>15,.0f}")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
