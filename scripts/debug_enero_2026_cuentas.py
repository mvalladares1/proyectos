"""
Debug de cuentas específicas en enero 2026
Comparar datos reales vs lo que calcula el servicio
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient
import json

def main():
    odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")
    
    # Cuentas a analizar
    cuentas_analizar = [
        '82010102',  # INTERESES POR LEASING
        '21010201',  # OBLIGACIONES POR LEASING POR PAGAR CP
        '21030201',  # PRESTAMOS EERR $
    ]
    
    print("="*100)
    print("DEBUG ENERO 2026 - ANÁLISIS DE DUPLICACIÓN")
    print("="*100)
    
    for codigo_cuenta in cuentas_analizar:
        print(f"\n{'='*100}")
        print(f"CUENTA: {codigo_cuenta}")
        print(f"{'='*100}")
        
        # 1. Buscar todas las líneas de la cuenta en enero 2026
        lineas = odoo.search_read(
            'account.move.line',
            [
                ['account_id.code', '=', codigo_cuenta],
                ['date', '>=', '2026-01-01'],
                ['date', '<=', '2026-01-31'],
                ['parent_state', 'in', ['posted', 'draft']]
            ],
            ['id', 'name', 'date', 'debit', 'credit', 'balance', 'move_id', 'account_id', 'partner_id'],
            limit=1000
        )
        
        print(f"\nTotal líneas encontradas: {len(lineas)}")
        
        total_debit = 0
        total_credit = 0
        total_balance = 0
        
        print(f"\n{'Fecha':<12} {'ID':<8} {'Asiento':<25} {'Débito':>15} {'Crédito':>15} {'Balance':>15} {'Descripción':<40}")
        print("-" * 150)
        
        for linea in lineas:
            fecha = linea.get('date', '')
            line_id = linea.get('id', 0)
            move = linea.get('move_id', [0, ''])[1] if linea.get('move_id') else ''
            debit = linea.get('debit', 0)
            credit = linea.get('credit', 0)
            balance = linea.get('balance', 0)
            nombre = linea.get('name', '')[:40]
            
            total_debit += debit
            total_credit += credit
            total_balance += balance
            
            print(f"{fecha:<12} {line_id:<8} {move:<25} {debit:>15,.0f} {credit:>15,.0f} {balance:>15,.0f} {nombre:<40}")
        
        print("-" * 150)
        print(f"{'TOTAL':<12} {'':<8} {'':<25} {total_debit:>15,.0f} {total_credit:>15,.0f} {total_balance:>15,.0f}")
        print(f"\nBalance total (Débito - Crédito): {total_balance:,.0f}")
        
        # 2. Ahora verificar cuántas veces aparece en asientos que tocan efectivo
        print(f"\n{'-'*100}")
        print("ANÁLISIS: ¿Estas líneas están en asientos que tocan efectivo?")
        print(f"{'-'*100}")
        
        # Para cada línea, verificar si está en un asiento que toca efectivo (110*, 111*)
        for linea in lineas:
            move_id = linea.get('move_id', [None])[0] if linea.get('move_id') else None
            if not move_id:
                continue
            
            # Buscar todas las líneas del asiento
            lineas_asiento = odoo.search_read(
                'account.move.line',
                [['move_id', '=', move_id]],
                ['id', 'account_id', 'debit', 'credit', 'balance'],
                limit=1000
            )
            
            # ¿Alguna cuenta empieza con 110 o 111?
            cuentas_en_asiento = []
            toca_efectivo = False
            for l in lineas_asiento:
                acc = l.get('account_id', [None, ''])[1] if l.get('account_id') else ''
                codigo = acc.split()[0] if acc else ''
                cuentas_en_asiento.append(codigo)
                if codigo.startswith('110') or codigo.startswith('111'):
                    toca_efectivo = True
            
            move_name = linea.get('move_id', [0, ''])[1]
            print(f"  Asiento {move_name}:")
            print(f"    {'SÍ TOCA EFECTIVO' if toca_efectivo else 'NO toca efectivo'}")
            print(f"    Cuentas: {', '.join(cuentas_en_asiento[:5])}")
        
        # 3. Verificar si está en mapeo_cuentas (parametrizada)
        with open('backend/data/mapeo_cuentas.json', 'r', encoding='utf-8') as f:
            mapeo = json.load(f)
        
        es_parametrizada = codigo_cuenta in mapeo.get('mapeo_cuentas', {})
        print(f"\n¿Está en mapeo_cuentas.json? {'SÍ' if es_parametrizada else 'NO'}")
        if es_parametrizada:
            concepto = mapeo['mapeo_cuentas'][codigo_cuenta]
            print(f"  Mapea a concepto: {concepto}")
        
        print(f"\n{'='*100}")
        print(f"CONCLUSIÓN PARA {codigo_cuenta}:")
        print(f"  - Balance real en Odoo: {total_balance:,.0f}")
        print(f"  - ¿Parametrizada?: {es_parametrizada}")
        print(f"  - Si aparece DUPLICADA, se está procesando 2 veces:")
        print(f"    1. En el flujo normal (asientos que tocan efectivo)")
        print(f"    2. En el paso 5a.1 (cuentas parametrizadas)")
        print(f"{'='*100}\n")

if __name__ == "__main__":
    main()
