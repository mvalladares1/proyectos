"""
Debug script para analizar facturas en borrador y abiertas para proyección de flujo de caja.
Período: 2026-11-01 a 2027-12-31
"""
import xmlrpc.client
import getpass
from datetime import datetime, timedelta

ODOO_URL = "https://riofuturo.server98c6e.oerpondemand.net"
ODOO_DB = "riofuturo-master"

# Configuración del período
FECHA_INICIO = "2026-11-01"
FECHA_FIN = "2027-12-31"

def main():
    print("=" * 80)
    print(f"DEBUG: Proyección Flujo de Caja")
    print(f"Período: {FECHA_INICIO} a {FECHA_FIN}")
    print("=" * 80)
    
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
    
    # =====================================================================
    # PASO 1: Buscar TODOS los account.move (facturas) en borrador o abiertos
    # =====================================================================
    print("\n--- PASO 1: Buscar documentos candidatos ---")
    
    # Domain base: Tipos y Estado
    domain_base = [
        ('move_type', 'in', ['out_invoice', 'in_invoice']),
        ('state', '!=', 'cancel'),
        '|', ('state', '=', 'draft'), '&', ('state', '=', 'posted'), ('payment_state', '!=', 'paid')
    ]
    
    # Domain con filtro de fechas para traer solo los relevantes
    # OR: x_studio_fecha_de_pago en rango, invoice_date_due en rango, invoice_date en rango
    domain_filtrado = domain_base + [
        '|', '|',
            '&', ('x_studio_fecha_de_pago', '>=', FECHA_INICIO), ('x_studio_fecha_de_pago', '<=', FECHA_FIN),
            '&', ('invoice_date_due', '>=', FECHA_INICIO), ('invoice_date_due', '<=', FECHA_FIN),
            '&', ('invoice_date', '>=', FECHA_INICIO), ('invoice_date', '<=', FECHA_FIN)
    ]
    
    campos = ['id', 'name', 'state', 'move_type', 'invoice_date', 'invoice_date_due', 
              'date', 'amount_total', 'partner_id', 'payment_state']
    
    # Intentar agregar x_studio_fecha_de_pago
    has_custom_field = False
    try:
        test_campos = campos + ['x_studio_fecha_de_pago']
        moves_test = search_read('account.move', [('id', '=', 1)], test_campos, limit=1)
        campos = test_campos
        has_custom_field = True
        print("✓ Campo x_studio_fecha_de_pago existe")
    except Exception as e:
        print(f"✗ Campo x_studio_fecha_de_pago NO existe: {e}")
        # Quitar el filtro de x_studio del domain si no existe
        domain_filtrado = domain_base + [
            '|',
                '&', ('invoice_date_due', '>=', FECHA_INICIO), ('invoice_date_due', '<=', FECHA_FIN),
                '&', ('invoice_date', '>=', FECHA_INICIO), ('invoice_date', '<=', FECHA_FIN)
        ]
    
    print(f"Buscando con filtro de fechas: {FECHA_INICIO} a {FECHA_FIN}")
    moves = search_read('account.move', domain_filtrado, campos, limit=500)
    
    print(f"\nTotal documentos encontrados (en rango de fechas): {len(moves)}")
    
    # =====================================================================
    # PASO 2: Analizar fechas de cada documento
    # =====================================================================
    print("\n--- PASO 2: Análisis de fechas por documento ---")
    
    en_rango = []
    fuera_rango = []
    
    for m in moves:
        # Calcular fecha de proyección
        fecha_pago = m.get('x_studio_fecha_de_pago') if 'x_studio_fecha_de_pago' in m else None
        fecha_venc = m.get('invoice_date_due')
        fecha_inv = m.get('invoice_date') or m.get('date')
        state = m.get('state')
        
        fecha_proy = None
        origen = ""
        
        if fecha_pago:
            fecha_proy = fecha_pago
            origen = "x_studio_fecha_de_pago"
        elif fecha_venc:
            fecha_proy = fecha_venc
            origen = "invoice_date_due"
        elif state == 'draft' and fecha_inv:
            # Estimación +30 días
            try:
                dt = datetime.strptime(fecha_inv, '%Y-%m-%d')
                fecha_proy = (dt + timedelta(days=30)).strftime('%Y-%m-%d')
                origen = f"invoice_date+30d ({fecha_inv})"
            except:
                pass
        
        if not fecha_proy:
            fecha_proy = fecha_inv
            origen = "fallback fecha_inv"
        
        # Verificar si está en rango
        en_periodo = False
        if fecha_proy:
            en_periodo = FECHA_INICIO <= fecha_proy <= FECHA_FIN
        
        doc_info = {
            'id': m['id'],
            'name': m.get('name', 'Sin nombre'),
            'state': state,
            'type': m.get('move_type'),
            'amount': m.get('amount_total', 0),
            'partner': m.get('partner_id')[1] if m.get('partner_id') else 'N/A',
            'fecha_inv': fecha_inv,
            'fecha_venc': fecha_venc,
            'fecha_pago': fecha_pago,
            'fecha_proy': fecha_proy,
            'origen': origen,
            'en_periodo': en_periodo
        }
        
        if en_periodo:
            en_rango.append(doc_info)
        else:
            fuera_rango.append(doc_info)
    
    # =====================================================================
    # PASO 3: Mostrar resultados
    # =====================================================================
    print(f"\n--- DOCUMENTOS EN RANGO ({len(en_rango)}) ---")
    for d in en_rango[:20]:  # Máximo 20
        print(f"  [{d['state'].upper()}] {d['name']}")
        print(f"      Partner: {d['partner']}")
        print(f"      Monto: ${d['amount']:,.0f}")
        print(f"      Fecha Factura: {d['fecha_inv']}")
        print(f"      Fecha Vencimiento: {d['fecha_venc']}")
        print(f"      Fecha Pago Acordada: {d['fecha_pago']}")
        print(f"      >>> Fecha Proyección: {d['fecha_proy']} ({d['origen']})")
        print()
    
    if len(en_rango) > 20:
        print(f"  ... y {len(en_rango) - 20} más")
    
    print(f"\n--- DOCUMENTOS FUERA DE RANGO ({len(fuera_rango)}) ---")
    for d in fuera_rango[:10]:  # Solo 10
        print(f"  [{d['state'].upper()}] {d['name']} | Fecha Proy: {d['fecha_proy']} ({d['origen']})")
    
    if len(fuera_rango) > 10:
        print(f"  ... y {len(fuera_rango) - 10} más")
    
    # =====================================================================
    # PASO 4: Verificar líneas de un documento en rango (si hay)
    # =====================================================================
    if en_rango:
        print("\n--- PASO 4: Líneas del primer documento en rango ---")
        sample_id = en_rango[0]['id']
        lines = search_read(
            'account.move.line',
            [('move_id', '=', sample_id), ('display_type', 'not in', ['line_section', 'line_note'])],
            ['name', 'account_id', 'price_subtotal'],
            limit=10
        )
        print(f"Documento: {en_rango[0]['name']} (ID: {sample_id})")
        for l in lines:
            acc = l.get('account_id')
            acc_str = f"{acc[1]}" if acc else "N/A"
            print(f"  - {l.get('name', 'Sin etiqueta')} | Cuenta: {acc_str} | Subtotal: ${l.get('price_subtotal', 0):,.0f}")
    
    print("\n" + "=" * 80)
    print("DEBUG COMPLETADO")
    print("=" * 80)

if __name__ == "__main__":
    main()
