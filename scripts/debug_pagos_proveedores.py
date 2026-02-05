"""
Debug: Análisis de Pagos a Proveedores (1.2.1)
=====================================

Objetivo: Entender estructura de datos para:
- REAL: Total pagado en el período (facturas pagadas)
- PROYECTADO: Importe adeudado de facturas parcialmente pagadas

Consulta el diario "Facturas de Proveedores"
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

# Credenciales estáticas para debug
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

def main():
    print("=" * 80)
    print("DEBUG: PAGOS A PROVEEDORES (1.2.1)")
    print("=" * 80)
    
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    
    # ==========================================
    # 1. BUSCAR DIARIOS DISPONIBLES
    # ==========================================
    print("\n[1] DIARIOS DISPONIBLES EN ODOO:")
    print("-" * 50)
    
    journals = odoo.search_read(
        'account.journal',
        [],
        ['id', 'name', 'code', 'type'],
        limit=50
    )
    
    journal_proveedores_id = None
    for j in journals:
        tipo_emoji = {'sale': '💰', 'purchase': '🛒', 'bank': '🏦', 'cash': '💵', 'general': '📋'}.get(j['type'], '❓')
        print(f"  {tipo_emoji} [{j['id']:3}] {j['name']:<35} | Code: {j['code']:<8} | Type: {j['type']}")
        if 'proveedor' in j['name'].lower():
            journal_proveedores_id = j['id']
    
    if not journal_proveedores_id:
        print("\n⚠️ No se encontró diario 'Facturas de Proveedores'. Buscando por tipo 'purchase'...")
        for j in journals:
            if j['type'] == 'purchase':
                journal_proveedores_id = j['id']
                print(f"  Usando: [{j['id']}] {j['name']}")
                break
    
    # ==========================================
    # 2. BUSCAR MOVE_TYPES DISPONIBLES
    # ==========================================
    print("\n[2] TIPOS DE MOVIMIENTOS (move_type):")
    print("-" * 50)
    
    # Obtener una muestra de moves para ver move_types
    moves_sample = odoo.search_read(
        'account.move',
        [['date', '>=', '2025-01-01']],
        ['move_type', 'journal_id', 'state'],
        limit=1000
    )
    
    move_types_count = {}
    for m in moves_sample:
        mt = m.get('move_type', 'N/A')
        jn = m['journal_id'][1] if m.get('journal_id') else 'N/A'
        key = (mt, jn)
        move_types_count[key] = move_types_count.get(key, 0) + 1
    
    for (mt, jn), count in sorted(move_types_count.items(), key=lambda x: -x[1]):
        print(f"  {mt:<20} | {jn:<30} | Count: {count}")
    
    # ==========================================
    # 3. FACTURAS DE PROVEEDORES - ENERO 2026
    # ==========================================
    print("\n[3] FACTURAS DE PROVEEDORES - ENERO 2026:")
    print("-" * 50)
    
    # Buscar facturas de proveedor
    facturas_proveedor = odoo.search_read(
        'account.move',
        [
            ['move_type', 'in', ['in_invoice', 'in_refund']],  # Facturas de proveedor
            ['date', '>=', '2026-01-01'],
            ['date', '<=', '2026-01-31'],
            ['state', '=', 'posted']
        ],
        ['id', 'name', 'ref', 'partner_id', 'invoice_date', 'date', 'amount_total', 
         'amount_residual', 'payment_state', 'state', 'move_type', 'journal_id'],
        limit=100,
        order='date desc'
    )
    
    print(f"  Total facturas encontradas: {len(facturas_proveedor)}")
    
    # Agrupar por payment_state
    by_payment_state = {}
    for f in facturas_proveedor:
        ps = f.get('payment_state', 'N/A')
        if ps not in by_payment_state:
            by_payment_state[ps] = {'count': 0, 'total': 0, 'residual': 0}
        by_payment_state[ps]['count'] += 1
        by_payment_state[ps]['total'] += f.get('amount_total', 0)
        by_payment_state[ps]['residual'] += f.get('amount_residual', 0)
    
    print("\n  Por estado de pago:")
    for ps, data in by_payment_state.items():
        emoji = {'paid': '✅', 'not_paid': '❌', 'partial': '⚡', 'reversed': '↩️'}.get(ps, '❓')
        print(f"    {emoji} {ps:<15} | Count: {data['count']:3} | Total: ${data['total']:>15,.0f} | Residual: ${data['residual']:>15,.0f}")
    
    # ==========================================
    # 4. DETALLE DE FACTURAS PAGADAS VS NO PAGADAS
    # ==========================================
    print("\n[4] DETALLE (Primeras 10 por cada estado):")
    print("-" * 50)
    
    for estado in ['paid', 'partial', 'not_paid']:
        facturas_estado = [f for f in facturas_proveedor if f.get('payment_state') == estado][:10]
        if facturas_estado:
            print(f"\n  === {estado.upper()} ===")
            for f in facturas_estado:
                partner = f['partner_id'][1][:30] if f.get('partner_id') else 'N/A'
                print(f"    {f['name']:<20} | {partner:<30} | Total: ${f.get('amount_total', 0):>12,.0f} | Residual: ${f.get('amount_residual', 0):>12,.0f}")
    
    # ==========================================
    # 5. VERIFICAR CUENTAS INVOLUCRADAS
    # ==========================================
    print("\n[5] CUENTAS INVOLUCRADAS EN FACTURAS DE PROVEEDOR:")
    print("-" * 50)
    
    if facturas_proveedor:
        # Tomar algunas facturas para ver sus líneas
        sample_ids = [f['id'] for f in facturas_proveedor[:20]]
        
        lineas = odoo.search_read(
            'account.move.line',
            [['move_id', 'in', sample_ids]],
            ['account_id', 'debit', 'credit', 'balance', 'move_id'],
            limit=500
        )
        
        cuentas_involucradas = {}
        for l in lineas:
            acc = l['account_id']
            if acc:
                acc_code = acc[1].split(' ')[0] if ' ' in acc[1] else acc[1]
                acc_name = acc[1]
                key = (acc_code, acc_name[:40])
                if key not in cuentas_involucradas:
                    cuentas_involucradas[key] = {'debit': 0, 'credit': 0, 'count': 0}
                cuentas_involucradas[key]['debit'] += l.get('debit', 0)
                cuentas_involucradas[key]['credit'] += l.get('credit', 0)
                cuentas_involucradas[key]['count'] += 1
        
        for (code, name), data in sorted(cuentas_involucradas.items()):
            print(f"  {code:<12} | D: ${data['debit']:>12,.0f} | C: ${data['credit']:>12,.0f} | N={data['count']}")
    
    # ==========================================
    # 6. ANÁLISIS PARA COLUMNAS REAL/PROYECTADO
    # ==========================================
    print("\n" + "=" * 80)
    print("RESUMEN PARA IMPLEMENTACIÓN:")
    print("=" * 80)
    
    total_pagado = sum(f.get('amount_total', 0) - f.get('amount_residual', 0) for f in facturas_proveedor if f.get('payment_state') in ['paid', 'partial'])
    total_pendiente = sum(f.get('amount_residual', 0) for f in facturas_proveedor if f.get('payment_state') in ['not_paid', 'partial'])
    
    print(f"""
    COLUMNA REAL (Efectivamente pagado):
    ------------------------------------
    - Facturas con payment_state = 'paid': amount_total completo
    - Facturas con payment_state = 'partial': (amount_total - amount_residual)
    
    TOTAL PAGADO ENE 2026: ${total_pagado:,.0f}
    
    COLUMNA PROYECTADO (Pendiente de pago):
    --------------------------------------
    - Facturas con payment_state = 'not_paid': amount_total completo
    - Facturas con payment_state = 'partial': amount_residual
    
    TOTAL PENDIENTE ENE 2026: ${total_pendiente:,.0f}
    """)

if __name__ == "__main__":
    main()
