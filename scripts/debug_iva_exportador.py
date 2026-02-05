"""
Debug: Análisis de IVA EXPORTADOR (1.2.6)
========================================

Objetivo: Buscar movimientos de la cuenta "11060108 DEVOLUCION IVA EXPORTADOR"
donde el partner sea "TESORERÍA GENERAL DE LA REPÚBLICA"

Para: 1.2.6 - Otras entradas (salidas) de efectivo
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
    print("DEBUG: IVA EXPORTADOR (1.2.6)")
    print("=" * 80)
    
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    
    # ==========================================
    # 1. BUSCAR LA CUENTA
    # ==========================================
    print("\n[1] BUSCANDO CUENTA 'DEVOLUCION IVA EXPORTADOR':")
    print("-" * 50)
    
    # Buscar por código y nombre
    cuentas_iva = odoo.search_read(
        'account.account',
        [
            '|', '|',
            ['code', 'ilike', '11060108'],
            ['name', 'ilike', 'IVA EXPORTADOR'],
            ['name', 'ilike', 'DEVOLUCION IVA']
        ],
        ['id', 'code', 'name'],
        limit=20
    )
    
    cuenta_iva_id = None
    for c in cuentas_iva:
        print(f"  [{c['id']:5}] {c['code']} - {c['name']}")
        if '11060108' in c['code']:
            cuenta_iva_id = c['id']
    
    if not cuenta_iva_id:
        print("\n  ⚠️ No se encontró cuenta exacta 11060108")
        # Buscar cualquier cuenta con IVA
        cuentas_iva = odoo.search_read(
            'account.account',
            [['name', 'ilike', 'IVA']],
            ['id', 'code', 'name'],
            limit=50
        )
        print("\n  Cuentas con 'IVA' en el nombre:")
        for c in cuentas_iva:
            print(f"    [{c['id']:5}] {c['code']} - {c['name']}")
    
    # ==========================================
    # 2. BUSCAR EL PARTNER "TESORERÍA"
    # ==========================================
    print("\n[2] BUSCANDO PARTNER 'TESORERÍA GENERAL DE LA REPÚBLICA':")
    print("-" * 50)
    
    partners_tesoreria = odoo.search_read(
        'res.partner',
        [
            '|', '|',
            ['name', 'ilike', 'TESORERIA'],
            ['name', 'ilike', 'TESORERÍA'],
            ['name', 'ilike', 'REPUBLICA']
        ],
        ['id', 'name', 'vat'],
        limit=20
    )
    
    partner_tesoreria_id = None
    for p in partners_tesoreria:
        print(f"  [{p['id']:5}] {p['name']:<50} | RUT: {p.get('vat', 'N/A')}")
        if 'TESORER' in p['name'].upper() and 'REPUBLICA' in p['name'].upper():
            partner_tesoreria_id = p['id']
    
    # ==========================================
    # 3. BUSCAR MOVIMIENTOS
    # ==========================================
    print("\n[3] MOVIMIENTOS EN CUENTA IVA EXPORTADOR:")
    print("-" * 50)
    
    if cuenta_iva_id:
        # Buscar movimientos de la cuenta
        movimientos_iva = odoo.search_read(
            'account.move.line',
            [
                ['account_id', '=', cuenta_iva_id],
                ['parent_state', '=', 'posted'],
                ['date', '>=', '2025-01-01']
            ],
            ['id', 'move_id', 'partner_id', 'date', 'name', 'debit', 'credit', 'balance'],
            limit=100,
            order='date desc'
        )
        
        print(f"  Total movimientos encontrados: {len(movimientos_iva)}")
        
        # Agrupar por partner
        by_partner = {}
        for m in movimientos_iva:
            partner = m['partner_id'][1] if m.get('partner_id') else 'Sin partner'
            partner_id = m['partner_id'][0] if m.get('partner_id') else 0
            if partner not in by_partner:
                by_partner[partner] = {'id': partner_id, 'count': 0, 'debit': 0, 'credit': 0}
            by_partner[partner]['count'] += 1
            by_partner[partner]['debit'] += m.get('debit', 0)
            by_partner[partner]['credit'] += m.get('credit', 0)
        
        print("\n  Por partner:")
        for partner, data in sorted(by_partner.items(), key=lambda x: -x[1]['count']):
            es_tesoreria = '✅' if 'TESORER' in partner.upper() else '  '
            print(f"  {es_tesoreria} [{data['id']:5}] {partner[:45]:<45} | N={data['count']:3} | D: ${data['debit']:>12,.0f} | C: ${data['credit']:>12,.0f}")
        
        # Mostrar detalle de movimientos con Tesorería
        print("\n  Detalle movimientos con TESORERÍA:")
        for m in movimientos_iva:
            partner = m['partner_id'][1] if m.get('partner_id') else ''
            if 'TESORER' in partner.upper():
                move_name = m['move_id'][1] if m.get('move_id') else 'N/A'
                print(f"    {m['date']} | {move_name:<25} | {m.get('name', '')[:30]:<30} | D: ${m.get('debit', 0):>12,.0f} | C: ${m.get('credit', 0):>12,.0f}")
    
    # ==========================================
    # 4. BÚSQUEDA ALTERNATIVA SI NO HAY CUENTA
    # ==========================================
    if not cuenta_iva_id:
        print("\n[4] BÚSQUEDA ALTERNATIVA - MOVIMIENTOS CON 'IVA EXPORTADOR' EN NOMBRE:")
        print("-" * 50)
        
        movimientos_alt = odoo.search_read(
            'account.move.line',
            [
                ['name', 'ilike', 'IVA EXPORTADOR'],
                ['parent_state', '=', 'posted'],
                ['date', '>=', '2025-01-01']
            ],
            ['id', 'move_id', 'account_id', 'partner_id', 'date', 'name', 'debit', 'credit'],
            limit=50
        )
        
        print(f"  Encontrados: {len(movimientos_alt)}")
        for m in movimientos_alt:
            acc = m['account_id'][1] if m.get('account_id') else 'N/A'
            partner = m['partner_id'][1][:30] if m.get('partner_id') else 'N/A'
            print(f"    {m['date']} | {acc[:20]:<20} | {partner:<30} | D: ${m.get('debit', 0):>12,.0f}")
    
    # ==========================================
    # 5. RESUMEN
    # ==========================================
    print("\n" + "=" * 80)
    print("RESUMEN PARA IMPLEMENTACIÓN 1.2.6:")
    print("=" * 80)
    print(f"""
    LÓGICA:
    -------
    1. Buscar en cuenta: 11060108 (DEVOLUCION IVA EXPORTADOR)
       Cuenta ID: {cuenta_iva_id or 'No encontrada'}
       
    2. Filtrar solo donde partner = 'TESORERÍA GENERAL DE LA REPÚBLICA'
       Partner ID: {partner_tesoreria_id or 'No encontrado'}
       
    3. Usar fecha del asiento (date) para agrupar por mes
    
    4. REAL = Movimientos ya registrados con débito (entrada de efectivo)
       PROYECTADO = Podría ser solicitudes pendientes de devolución
    """)

if __name__ == "__main__":
    main()
