"""
Debug script que simula exactamente lo que hace el servicio de flujo de caja.
Esto ayuda a identificar dónde falla la lógica.
"""
import xmlrpc.client
import getpass
from datetime import datetime, timedelta

ODOO_URL = "https://riofuturo.server98c6e.oerpondemand.net"
ODOO_DB = "riofuturo-master"

FECHA_INICIO = "2026-11-01"
FECHA_FIN = "2027-12-31"

def main():
    print("=" * 100)
    print(f"DEBUG: Simulación de _calcular_flujo_proyectado")
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
    
    def search_read(model, domain, fields, limit=2000):
        return models.execute_kw(ODOO_DB, uid, api_key, model, 'search_read', [domain], {'fields': fields, 'limit': limit})
    
    # =========================================================================
    # PASO 1: Exactamente igual que el servicio - buscar moves
    # =========================================================================
    print("\n--- PASO 1: Buscar account.move (igual que servicio) ---")
    
    domain_base = [
        ('move_type', 'in', ['out_invoice', 'in_invoice']),
        ('state', '!=', 'cancel'),
        '|', ('state', '=', 'draft'), '&', ('state', '=', 'posted'), ('payment_state', '!=', 'paid')
    ]
    
    # Domain CON filtro de x_studio_fecha_de_pago
    domain = domain_base + [
        '|', '|',
            '&', ('x_studio_fecha_de_pago', '>=', FECHA_INICIO), ('x_studio_fecha_de_pago', '<=', FECHA_FIN),
            '&', ('invoice_date_due', '>=', FECHA_INICIO), ('invoice_date_due', '<=', FECHA_FIN),
            '&', ('invoice_date', '>=', FECHA_INICIO), ('invoice_date', '<=', FECHA_FIN)
    ]
    
    campos_move = ['id', 'name', 'ref', 'partner_id', 'invoice_date', 'invoice_date_due', 'amount_total',
                   'amount_residual', 'move_type', 'state', 'payment_state', 'date', 'x_studio_fecha_de_pago']
    
    print(f"Domain: {domain}")
    
    try:
        moves = search_read('account.move', domain, campos_move, limit=2000)
        print(f"✅ Moves encontrados: {len(moves)}")
    except Exception as e:
        print(f"❌ Error buscando moves: {e}")
        # Fallback sin x_studio
        if "x_studio_fecha_de_pago" in str(e):
            print("Reintentando sin x_studio_fecha_de_pago...")
            campos_move.remove('x_studio_fecha_de_pago')
            domain = domain_base + [
                '|',
                    '&', ('invoice_date_due', '>=', FECHA_INICIO), ('invoice_date_due', '<=', FECHA_FIN),
                    '&', ('invoice_date', '>=', FECHA_INICIO), ('invoice_date', '<=', FECHA_FIN)
            ]
            moves = search_read('account.move', domain, campos_move, limit=2000)
            print(f"✅ Moves encontrados (sin custom field): {len(moves)}")
        else:
            return
    
    if not moves:
        print("⚠️ NO HAY MOVES - Aquí termina el servicio con proyección vacía")
        return
    
    # Mostrar algunos moves
    print("\nPrimeros 5 moves:")
    for m in moves[:5]:
        print(f"  [{m['state']}] {m['name']} | Partner: {m['partner_id'][1] if m['partner_id'] else 'N/A'} | Amount: ${m['amount_total']:,.0f}")
    
    # =========================================================================
    # PASO 2: Obtener líneas de los moves
    # =========================================================================
    print("\n--- PASO 2: Buscar account.move.line ---")
    
    move_ids = [m['id'] for m in moves]
    
    # Domain CON display_type (corregido)
    domain_lines = [
        ('move_id', 'in', move_ids),
        ('display_type', 'not in', ['line_section', 'line_note'])
    ]
    
    campos_lines = ['move_id', 'account_id', 'price_subtotal', 'name', 'display_type']
    
    try:
        lines = search_read('account.move.line', domain_lines, campos_lines, limit=10000)
        print(f"✅ Líneas encontradas: {len(lines)}")
    except Exception as e:
        print(f"❌ Error buscando líneas: {e}")
        return
    
    if not lines:
        print("⚠️ NO HAY LÍNEAS - Aquí termina el servicio con proyección vacía")
        return
    
    # Mostrar algunas líneas
    print("\nPrimeras 5 líneas:")
    for l in lines[:5]:
        acc = l.get('account_id')
        acc_str = f"{acc[0]} - {acc[1]}" if acc else "N/A"
        print(f"  {l.get('name', 'Sin nombre')[:40]} | Cuenta: {acc_str} | Subtotal: ${l.get('price_subtotal', 0):,.0f}")
    
    # Agrupar líneas por move_id
    lines_by_move = {}
    for l in lines:
        mid = l['move_id'][0] if isinstance(l.get('move_id'), (list, tuple)) else l.get('move_id')
        lines_by_move.setdefault(mid, []).append(l)
    
    print(f"\nMoves con líneas: {len(lines_by_move)}")
    
    # =========================================================================
    # PASO 3: Simular clasificación y cálculo de montos
    # =========================================================================
    print("\n--- PASO 3: Simular clasificación ---")
    
    total_out_invoice = 0  # Clientes (ingresos)
    total_in_invoice = 0   # Proveedores (egresos)
    
    for move in moves:
        move_id = move['id']
        move_type = move.get('move_type')
        move_lines = lines_by_move.get(move_id, [])
        
        for line in move_lines:
            subtotal = line.get('price_subtotal', 0)
            if subtotal == 0:
                continue
                
            if move_type == 'out_invoice':
                total_out_invoice += subtotal
            elif move_type == 'in_invoice':
                total_in_invoice += subtotal
    
    print(f"\n📊 RESULTADOS DE SIMULACIÓN:")
    print(f"   Total facturas cliente (out_invoice): ${total_out_invoice:,.0f}")
    print(f"   Total facturas proveedor (in_invoice): ${total_in_invoice:,.0f}")
    print(f"   Neto: ${total_out_invoice - total_in_invoice:,.0f}")
    
    # =========================================================================
    # PASO 4: Verificar cuentas y mapeo
    # =========================================================================
    print("\n--- PASO 4: Cuentas encontradas ---")
    
    account_ids = list(set(
        l['account_id'][0] if isinstance(l.get('account_id'), (list, tuple)) else l.get('account_id')
        for l in lines if l.get('account_id')
    ))
    
    print(f"Total cuentas únicas: {len(account_ids)}")
    
    if account_ids:
        acc_read = search_read('account.account', [('id', 'in', account_ids[:20])], ['code', 'name'], limit=20)
        print("\nCuentas (primeras 20):")
        for a in acc_read:
            print(f"  {a['code']} - {a['name']}")
    
    print("\n" + "=" * 100)
    print("DEBUG COMPLETADO")
    print("=" * 100)

if __name__ == "__main__":
    main()
