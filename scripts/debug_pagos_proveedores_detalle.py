"""
Debug: Análisis detallado de Pagos a Proveedores para 1.2.1
============================================================

Analiza los diferentes tipos de documentos en el diario de proveedores:
- Facturas de proveedor (in_invoice)
- Notas de crédito (in_refund)
- Distintos journals

Para entender cómo calcular REAL y PROYECTADO correctamente.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient
from datetime import datetime
from collections import defaultdict

# Credenciales estáticas para debug
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'


def main():
    print("=" * 80)
    print("DEBUG: TIPOS DE DOCUMENTOS EN PAGOS A PROVEEDORES")
    print("=" * 80)
    
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    
    # Período de análisis
    fecha_inicio = '2026-01-01'
    fecha_fin = '2026-01-31'
    
    print(f"\nPeríodo: {fecha_inicio} a {fecha_fin}")
    
    # ==========================================
    # 1. TODOS LOS MOVE_TYPES DE TIPO PURCHASE
    # ==========================================
    print("\n[1] DIARIOS TIPO 'PURCHASE':")
    print("-" * 50)
    
    journals_purchase = odoo.search_read(
        'account.journal',
        [['type', '=', 'purchase']],
        ['id', 'name', 'code'],
        limit=20
    )
    
    journal_ids = [j['id'] for j in journals_purchase]
    for j in journals_purchase:
        print(f"  [{j['id']:3}] {j['name']:<40} | Code: {j['code']}")
    
    # ==========================================
    # 2. FACTURAS POR TIPO Y DIARIO
    # ==========================================
    print("\n[2] FACTURAS POR TIPO Y DIARIO:")
    print("-" * 50)
    
    facturas = odoo.search_read(
        'account.move',
        [
            ['move_type', 'in', ['in_invoice', 'in_refund']],
            ['date', '>=', fecha_inicio],
            ['date', '<=', fecha_fin],
            ['state', '=', 'posted']
        ],
        ['id', 'name', 'move_type', 'journal_id', 'amount_total', 'amount_residual', 
         'payment_state', 'partner_id'],
        limit=2000
    )
    
    print(f"  Total facturas: {len(facturas)}")
    
    # Agrupar por journal y move_type
    por_journal_type = defaultdict(lambda: {'count': 0, 'total': 0, 'pagado': 0, 'residual': 0})
    
    for f in facturas:
        journal = f['journal_id'][1] if f.get('journal_id') else 'Sin Diario'
        move_type = f.get('move_type', 'N/A')
        key = (journal, move_type)
        
        total = f.get('amount_total', 0)
        residual = f.get('amount_residual', 0)
        pagado = total - residual
        
        por_journal_type[key]['count'] += 1
        por_journal_type[key]['total'] += total
        por_journal_type[key]['pagado'] += pagado
        por_journal_type[key]['residual'] += residual
    
    print(f"\n  {'Diario':<35} | {'Tipo':<12} | {'Count':>6} | {'Total':>15} | {'Pagado':>15} | {'Residual':>15}")
    print("  " + "-" * 110)
    
    for (journal, move_type), data in sorted(por_journal_type.items()):
        print(f"  {journal[:35]:<35} | {move_type:<12} | {data['count']:>6} | ${data['total']:>13,.0f} | ${data['pagado']:>13,.0f} | ${data['residual']:>13,.0f}")
    
    # ==========================================
    # 3. ANÁLISIS POR PAYMENT_STATE
    # ==========================================
    print("\n[3] ANÁLISIS POR PAYMENT_STATE:")
    print("-" * 50)
    
    por_estado = defaultdict(lambda: {'count': 0, 'total': 0, 'pagado': 0, 'residual': 0, 'facturas': []})
    
    for f in facturas:
        estado = f.get('payment_state', 'N/A')
        move_type = f.get('move_type', '')
        
        total = f.get('amount_total', 0)
        residual = f.get('amount_residual', 0)
        pagado = total - residual
        
        # Signo: notas de crédito son negativas
        signo = -1 if move_type == 'in_refund' else 1
        
        por_estado[estado]['count'] += 1
        por_estado[estado]['total'] += total * signo
        por_estado[estado]['pagado'] += pagado * signo
        por_estado[estado]['residual'] += residual * signo
        
        if len(por_estado[estado]['facturas']) < 3:
            por_estado[estado]['facturas'].append({
                'name': f['name'],
                'partner': f['partner_id'][1][:30] if f.get('partner_id') else 'N/A',
                'total': total,
                'residual': residual,
                'type': move_type
            })
    
    ESTADO_EMOJIS = {
        'paid': '✅',
        'not_paid': '❌',
        'partial': '⚡',
        'reversed': '↩️',
        'in_payment': '🔄'
    }
    
    print(f"\n  {'Estado':<15} | {'Count':>6} | {'Total (neto)':>18} | {'Pagado':>18} | {'Residual':>18}")
    print("  " + "-" * 90)
    
    for estado, data in sorted(por_estado.items()):
        emoji = ESTADO_EMOJIS.get(estado, '❓')
        print(f"  {emoji} {estado:<12} | {data['count']:>6} | ${data['total']:>16,.0f} | ${data['pagado']:>16,.0f} | ${data['residual']:>16,.0f}")
        
        # Mostrar ejemplos
        for ej in data['facturas']:
            tipo_indicator = '(NC)' if ej['type'] == 'in_refund' else '(FC)'
            print(f"       {tipo_indicator} {ej['name']:<20} | {ej['partner']:<30} | ${ej['total']:>12,.0f} | ${ej['residual']:>12,.0f}")
    
    # ==========================================
    # 4. CÁLCULO REAL Y PROYECTADO
    # ==========================================
    print("\n" + "=" * 80)
    print("CÁLCULO FINAL PARA 1.2.1 - PAGOS A PROVEEDORES")
    print("=" * 80)
    
    # REAL = Todo lo efectivamente pagado (paid + partial ya pagado)
    # PROYECTADO = Todo lo pendiente de pago (not_paid + partial residual)
    
    real_total = 0
    proyectado_total = 0
    
    for f in facturas:
        total = f.get('amount_total', 0)
        residual = f.get('amount_residual', 0)
        move_type = f.get('move_type', '')
        
        signo = -1 if move_type == 'in_refund' else 1
        
        pagado = (total - residual) * signo
        pendiente = residual * signo
        
        real_total += pagado
        proyectado_total += pendiente
    
    print(f"""
    ENERO 2026:
    -----------
    
    📊 REAL (Efectivamente pagado):     ${real_total:>18,.0f}
       - Facturas pagadas completas
       - Porción pagada de facturas parciales
       - Notas de crédito aplicadas (negativas)
    
    📈 PROYECTADO (Pendiente de pago):  ${proyectado_total:>18,.0f}
       - Facturas no pagadas
       - Porción pendiente de facturas parciales
    
    📋 PPTO (Presupuesto):              $                 0
       - Vacío por ahora
    
    ═══════════════════════════════════════════════════════════
    NOTA: Los valores son NEGATIVOS en el flujo (salidas de efectivo)
    
    Para el flujo de caja, aplicar signo negativo:
    - REAL en flujo:      ${-real_total:>18,.0f}
    - PROYECTADO en flujo: ${-proyectado_total:>18,.0f}
    """)
    
    # ==========================================
    # 5. DESGLOSE MENSUAL
    # ==========================================
    print("\n[5] DESGLOSE POR MES:")
    print("-" * 50)
    
    por_mes = defaultdict(lambda: {'real': 0, 'proyectado': 0})
    
    for f in facturas:
        fecha = f.get('date', '')
        if not fecha:
            continue
        mes = fecha[:7]
        
        total = f.get('amount_total', 0)
        residual = f.get('amount_residual', 0)
        move_type = f.get('move_type', '')
        
        signo = -1 if move_type == 'in_refund' else 1
        
        por_mes[mes]['real'] += (total - residual) * signo
        por_mes[mes]['proyectado'] += residual * signo
    
    print(f"\n  {'Mes':<10} | {'REAL':>18} | {'PROYECTADO':>18}")
    print("  " + "-" * 50)
    
    for mes in sorted(por_mes.keys()):
        data = por_mes[mes]
        print(f"  {mes:<10} | ${data['real']:>16,.0f} | ${data['proyectado']:>16,.0f}")


if __name__ == "__main__":
    main()
