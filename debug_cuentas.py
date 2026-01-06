"""
Debug script para analizar movimientos de cuentas de financiamiento.
Período: 2026-11-01 a 2027-12-31
"""
import xmlrpc.client
import getpass
from datetime import datetime

ODOO_URL = "https://riofuturo.server98c6e.oerpondemand.net"
ODOO_DB = "riofuturo-master"

# Configuración del período
FECHA_INICIO = "2026-11-01"
FECHA_FIN = "2027-12-31"

# Cuentas a analizar (de la imagen)
CUENTAS_OBJETIVO = [
    "21010101",  # PRESTAMOS CP BANCOS $
    "21010102",  # PRESTAMOS CP BANCOS US$
    "21010103",  # PRESTAMOS CP BANCOS UF
    "21010201",  # OBLIGACIONES POR LEASING POR PAGAR CP
    "21010204",  # INTERESES DIFERIDOS LEASING CP BANCO
    "21010202",  # OBLIGACIONES POR LEASING POR PAGAR LP
    "21010213",  # PRESTAMOS LP BANCOS $
    "21010223",  # PRESTAMOS LP BANCOS US$
    "21030201",  # PRESTAMOS EERR $
    "21030211",  # PRESTAMOS EERR US$
    "22010101",  # PRESTAMOS BANCARIOS LP UF
    "22010202",  # INTERESES DIFERIDOS LEASING LP BANCOS
    "22010204",  # INTERESES DIFERIDOS LEASING LP BANCO BCI
    "22020101",  # PRESTAMO EERR NO CORRIENTES
    "82010101",  # INTERESES FINANCIEROS
    "82010102",  # INTERESES POR LEASING
]

def main():
    print("=" * 100)
    print(f"DEBUG: Movimientos de Cuentas de Financiamiento")
    print(f"Período: {FECHA_INICIO} a {FECHA_FIN}")
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
    
    def search_read(model, domain, fields, limit=1000):
        return models.execute_kw(ODOO_DB, uid, api_key, model, 'search_read', [domain], {'fields': fields, 'limit': limit})
    
    # =====================================================================
    # PASO 1: Obtener IDs de las cuentas objetivo
    # =====================================================================
    print("\n--- PASO 1: Buscar cuentas objetivo ---")
    
    cuentas = search_read(
        'account.account',
        [('code', 'in', CUENTAS_OBJETIVO)],
        ['id', 'code', 'name'],
        limit=50
    )
    
    cuenta_map = {c['code']: {'id': c['id'], 'name': c['name']} for c in cuentas}
    cuenta_ids = [c['id'] for c in cuentas]
    
    print(f"Cuentas encontradas: {len(cuentas)}")
    for c in cuentas:
        print(f"  {c['code']} - {c['name']}")
    
    # Verificar cuentas no encontradas
    encontradas = set(c['code'] for c in cuentas)
    no_encontradas = set(CUENTAS_OBJETIVO) - encontradas
    if no_encontradas:
        print(f"\n⚠️ Cuentas NO encontradas: {no_encontradas}")
    
    # =====================================================================
    # PASO 2: Buscar movimientos de estas cuentas en el período
    # =====================================================================
    print(f"\n--- PASO 2: Movimientos en período {FECHA_INICIO} a {FECHA_FIN} ---")
    
    # Buscar TODOS los movimientos (posted y draft) para estas cuentas
    domain_lines = [
        ('account_id', 'in', cuenta_ids),
        ('date', '>=', FECHA_INICIO),
        ('date', '<=', FECHA_FIN),
        # Incluir draft y posted
        ('parent_state', 'in', ['draft', 'posted'])
    ]
    
    campos = ['account_id', 'move_id', 'name', 'date', 'debit', 'credit', 'balance', 'parent_state']
    
    lines = search_read('account.move.line', domain_lines, campos, limit=500)
    
    print(f"\nTotal líneas encontradas: {len(lines)}")
    
    # =====================================================================
    # PASO 3: Agrupar por cuenta y mostrar resumen
    # =====================================================================
    print("\n--- PASO 3: Resumen por cuenta ---")
    
    resumen = {}
    for code in CUENTAS_OBJETIVO:
        if code in cuenta_map:
            resumen[code] = {
                'nombre': cuenta_map[code]['name'],
                'id': cuenta_map[code]['id'],
                'total_debit': 0,
                'total_credit': 0,
                'total_balance': 0,
                'draft_count': 0,
                'posted_count': 0,
                'lineas': []
            }
    
    for line in lines:
        acc_id = line['account_id'][0] if line.get('account_id') else None
        # Buscar código por ID
        code = None
        for c, info in cuenta_map.items():
            if info['id'] == acc_id:
                code = c
                break
        
        if code and code in resumen:
            resumen[code]['total_debit'] += line.get('debit', 0)
            resumen[code]['total_credit'] += line.get('credit', 0)
            resumen[code]['total_balance'] += line.get('balance', 0)
            if line.get('parent_state') == 'draft':
                resumen[code]['draft_count'] += 1
            else:
                resumen[code]['posted_count'] += 1
            resumen[code]['lineas'].append(line)
    
    # Mostrar resumen
    print(f"\n{'Código':<12} {'Nombre':<45} {'Débito':>15} {'Crédito':>15} {'Balance':>15} {'Draft':>6} {'Posted':>6}")
    print("-" * 120)
    
    for code in CUENTAS_OBJETIVO:
        if code in resumen:
            r = resumen[code]
            nombre_corto = r['nombre'][:42] + "..." if len(r['nombre']) > 45 else r['nombre']
            print(f"{code:<12} {nombre_corto:<45} {r['total_debit']:>15,.0f} {r['total_credit']:>15,.0f} {r['total_balance']:>15,.0f} {r['draft_count']:>6} {r['posted_count']:>6}")
    
    # =====================================================================
    # PASO 4: Detalle de movimientos para cuentas con actividad
    # =====================================================================
    print("\n--- PASO 4: Detalle de movimientos (primeras 5 líneas por cuenta) ---")
    
    for code in CUENTAS_OBJETIVO:
        if code in resumen and len(resumen[code]['lineas']) > 0:
            print(f"\n📊 {code} - {resumen[code]['nombre']}")
            for i, line in enumerate(resumen[code]['lineas'][:5]):
                move_name = line['move_id'][1] if line.get('move_id') else 'N/A'
                state_emoji = "📝" if line.get('parent_state') == 'draft' else "✅"
                print(f"  {state_emoji} {line['date']} | {move_name[:40]:<40} | {line.get('name', '')[:30]:<30} | Balance: ${line.get('balance', 0):,.0f}")
            
            if len(resumen[code]['lineas']) > 5:
                print(f"  ... y {len(resumen[code]['lineas']) - 5} líneas más")
    
    # =====================================================================
    # PASO 5: Investigar cuentas SIN actividad en el período
    # =====================================================================
    print("\n--- PASO 5: Investigar cuentas SIN movimientos en el período ---")
    
    cuentas_sin_actividad = [code for code in CUENTAS_OBJETIVO if code in resumen and len(resumen[code]['lineas']) == 0]
    
    if not cuentas_sin_actividad:
        print("✅ Todas las cuentas tienen movimientos en el período")
    else:
        print(f"Cuentas sin movimientos: {len(cuentas_sin_actividad)}")
        
        for code in cuentas_sin_actividad:
            acc_id = cuenta_map[code]['id']
            
            # Buscar CUALQUIER movimiento de esta cuenta (sin filtro de fecha)
            any_lines = search_read(
                'account.move.line',
                [('account_id', '=', acc_id)],
                ['date', 'move_id', 'debit', 'credit', 'balance', 'parent_state'],
                limit=10
            )
            
            if not any_lines:
                print(f"\n  ❌ {code} - {resumen[code]['nombre']}")
                print(f"      >>> NO tiene NINGÚN movimiento en Odoo")
            else:
                # Encontrar rango de fechas
                fechas = [l['date'] for l in any_lines if l.get('date')]
                fecha_min = min(fechas) if fechas else "N/A"
                fecha_max = max(fechas) if fechas else "N/A"
                
                # Contar por estado
                draft_count = sum(1 for l in any_lines if l.get('parent_state') == 'draft')
                posted_count = sum(1 for l in any_lines if l.get('parent_state') == 'posted')
                
                print(f"\n  🔍 {code} - {resumen[code]['nombre']}")
                print(f"      >>> Tiene movimientos pero FUERA del período solicitado")
                print(f"      >>> Fechas encontradas: {fecha_min} a {fecha_max}")
                print(f"      >>> Estados: {draft_count} draft, {posted_count} posted")
                
                # Mostrar algunas líneas
                for line in any_lines[:3]:
                    move_name = line['move_id'][1] if line.get('move_id') else 'N/A'
                    state = "📝" if line.get('parent_state') == 'draft' else "✅"
                    print(f"      {state} {line['date']} | {move_name[:50]} | Balance: ${line.get('balance', 0):,.0f}")

    print("\n" + "=" * 100)
    print("DEBUG COMPLETADO")
    print("=" * 100)

if __name__ == "__main__":
    main()
