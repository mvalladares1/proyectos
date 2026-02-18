"""
Script para analizar las facturas revertidas (N/C - Notas de Crédito).
Muestra cómo se clasifican y cómo afectan los totales.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shared.odoo_client import OdooClient
from collections import defaultdict

def format_money(value):
    """Formatea un número como moneda chilena."""
    if value < 0:
        return f"-${abs(value):,.0f}".replace(',', '.')
    return f"${value:,.0f}".replace(',', '.')

def main():
    print("\n" + "="*80)
    print("ANÁLISIS DE FACTURAS REVERTIDAS (NOTAS DE CRÉDITO)")
    print("="*80 + "\n")
    
    odoo = OdooClient()
    
    fecha_inicio = '2026-01-01'
    fecha_fin = '2026-02-28'
    
    # Buscar TODAS las facturas
    todas_facturas = odoo.search_read(
        'account.move',
        [
            ['move_type', 'in', ['in_invoice', 'in_refund']],
            ['journal_id', '=', 2],
            ['date', '>=', fecha_inicio],
            ['date', '<=', fecha_fin],
            ['state', '=', 'posted']
        ],
        ['id', 'name', 'move_type', 'date', 'amount_total', 'amount_residual', 'partner_id'],
        limit=5000
    )
    
    # Separar por tipo
    facturas_normales = [f for f in todas_facturas if f.get('move_type') == 'in_invoice']
    facturas_revertidas = [f for f in todas_facturas if f.get('move_type') == 'in_refund']
    
    print(f"Total facturas: {len(todas_facturas)}")
    print(f"  - Facturas normales (in_invoice): {len(facturas_normales)}")
    print(f"  - Notas de crédito (in_refund):   {len(facturas_revertidas)}")
    print()
    
    # Obtener líneas de las N/C
    nc_ids = [f['id'] for f in facturas_revertidas]
    if nc_ids:
        lineas_nc = odoo.search_read(
            'account.move.line',
            [['move_id', 'in', nc_ids]],
            ['id', 'move_id', 'matching_number', 'date', 'debit', 'credit'],
            limit=50000
        )
        
        # Agrupar líneas por factura
        lineas_por_factura = defaultdict(list)
        for linea in lineas_nc:
            move_id = linea.get('move_id')
            if isinstance(move_id, (list, tuple)):
                move_id = move_id[0]
            lineas_por_factura[move_id].append(linea)
    else:
        lineas_por_factura = {}
    
    # Clasificar N/C por matching_number
    nc_clasificadas = {
        'PAGADAS_A': [],
        'PARCIALES_P': [],
        'NO_PAGADAS': [],
        'OTROS': []
    }
    
    for nc in facturas_revertidas:
        lineas = lineas_por_factura.get(nc['id'], [])
        
        # Detectar matching_number
        matching_number = None
        for linea in lineas:
            match = linea.get('matching_number')
            if match and match not in ['False', False, '', None]:
                matching_number = match
                break
        
        # Clasificar
        if matching_number and str(matching_number).startswith('A'):
            categoria = 'PAGADAS_A'
        elif matching_number == 'P':
            categoria = 'PARCIALES_P'
        elif not matching_number or matching_number in ['False', False, '', None]:
            categoria = 'NO_PAGADAS'
        else:
            categoria = 'OTROS'
        
        nc_clasificadas[categoria].append({
            'id': nc['id'],
            'name': nc.get('name', ''),
            'matching_number': matching_number,
            'amount_total': nc.get('amount_total', 0),
            'amount_residual': nc.get('amount_residual', 0),
            'partner': nc.get('partner_id', [0, 'Sin nombre'])[1] if isinstance(nc.get('partner_id'), (list, tuple)) else 'Sin nombre',
            'date': nc.get('date', '')
        })
    
    # Mostrar análisis detallado
    print("="*80)
    print("CLASIFICACIÓN DE NOTAS DE CRÉDITO POR MATCHING_NUMBER")
    print("="*80 + "\n")
    
    for cat_name, ncs in nc_clasificadas.items():
        if not ncs:
            continue
        
        total_monto = sum(nc['amount_total'] for nc in ncs)
        total_residual = sum(nc['amount_residual'] for nc in ncs)
        total_pagado = total_monto - total_residual
        
        print(f"\n📌 {cat_name}: {len(ncs)} N/C")
        print("-" * 80)
        print(f"  Monto total (POSITIVO en Odoo): {format_money(total_monto)}")
        print(f"  Residual total:                 {format_money(total_residual)}")
        print(f"  Devuelto (total - residual):    {format_money(total_pagado)}")
        
        print(f"\n  Todas las N/C de esta categoría:")
        for i, nc in enumerate(ncs, 1):
            pagado = nc['amount_total'] - nc['amount_residual']
            print(f"    {i}. {nc['name']:20} | Match: {str(nc['matching_number']):10} | Total: {format_money(nc['amount_total']):>15} | Residual: {format_money(nc['amount_residual']):>15} | Devuelto: {format_money(pagado):>15} | {nc['partner'][:30]}")
    
    # Explicar el impacto en flujo de caja
    print("\n" + "="*80)
    print("IMPACTO EN FLUJO DE CAJA")
    print("="*80)
    print("""
LÓGICA IMPLEMENTADA PARA N/C (move_type = 'in_refund'):
---------------------------------------------------------

1. SIGNO INVERTIDO: signo = -1 (las N/C SUMAN dinero, devuelven efectivo)
   
2. Para N/C PAGADAS (AXXXXX):
   - monto_real = -(amount_total - residual) * (-1) = +(amount_total - residual)
   - Es decir: SUMA en flujo REAL (dinero que YA nos devolvieron)
   
3. Para N/C PARCIALES (P):
   - monto_real = -(amount_total - residual) * (-1) = +(amount_total - residual)
   - monto_proyectado = -residual * (-1) = +residual
   - Es decir: Parte devuelta en REAL, parte pendiente en PROYECTADO
   
4. Para N/C NO PAGADAS (blank):
   - monto_real = 0
   - monto_proyectado = -amount_total * (-1) = +amount_total
   - Es decir: Todo el monto se espera recibir en PROYECTADO

RESULTADO: Las N/C aparecen como INGRESOS (+) en el flujo de caja, compensando
las facturas de proveedores que son EGRESOS (-)
""")
    
    # Calcular impacto numérico
    print("\n" + "="*80)
    print("IMPACTO NUMÉRICO TOTAL DE LAS N/C")
    print("="*80 + "\n")
    
    total_nc_monto = sum(nc.get('amount_total', 0) for nc in facturas_revertidas)
    total_nc_residual = sum(nc.get('amount_residual', 0) for nc in facturas_revertidas)
    total_nc_devuelto = total_nc_monto - total_nc_residual
    
    print(f"Total N/C - Monto bruto:           {format_money(total_nc_monto)}")
    print(f"Total N/C - Residual pendiente:    {format_money(total_nc_residual)}")
    print(f"Total N/C - Ya devuelto:           {format_money(total_nc_devuelto)}")
    print()
    print(f"Impacto en REAL (con signo invertido):       {format_money(total_nc_devuelto)} → +{format_money(total_nc_devuelto)}")
    print(f"Impacto en PROYECTADO (con signo invertido): {format_money(total_nc_residual)} → +{format_money(total_nc_residual)}")
    print()
    print("INTERPRETACIÓN:")
    print(f"  - Ya recibimos {format_money(total_nc_devuelto)} de devoluciones (REDUCE el flujo negativo)")
    print(f"  - Esperamos recibir {format_money(total_nc_residual)} más (REDUCE el flujo proyectado)")
    
    # Comparar con facturas normales
    print("\n" + "="*80)
    print("BALANCE: FACTURAS vs NOTAS DE CRÉDITO")
    print("="*80 + "\n")
    
    total_facturas_monto = sum(f.get('amount_total', 0) for f in facturas_normales)
    total_facturas_residual = sum(f.get('amount_residual', 0) for f in facturas_normales)
    total_facturas_pagado = total_facturas_monto - total_facturas_residual
    
    print(f"FACTURAS NORMALES ({len(facturas_normales)}):")
    print(f"  Monto total:    {format_money(total_facturas_monto)}")
    print(f"  Ya pagado:      {format_money(total_facturas_pagado)}")
    print(f"  Pendiente:      {format_money(total_facturas_residual)}")
    print()
    print(f"NOTAS DE CRÉDITO ({len(facturas_revertidas)}):")
    print(f"  Monto total:    {format_money(total_nc_monto)}")
    print(f"  Ya devuelto:    {format_money(total_nc_devuelto)}")
    print(f"  Pendiente:      {format_money(total_nc_residual)}")
    print()
    print("EFECTO NETO EN FLUJO DE CAJA:")
    neto_pagado = total_facturas_pagado - total_nc_devuelto
    neto_pendiente = total_facturas_residual - total_nc_residual
    print(f"  REAL neto:       -{format_money(total_facturas_pagado)} + {format_money(total_nc_devuelto)} = -{format_money(neto_pagado)}")
    print(f"  PROYECTADO neto: -{format_money(total_facturas_residual)} + {format_money(total_nc_residual)} = -{format_money(neto_pendiente)}")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
