"""
Script para analizar en detalle las categorizaciones de facturas por matching_number.
Muestra ejemplos de cada categoría y el conteo.
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
    print("ANÁLISIS DETALLADO DE CLASIFICACIÓN POR MATCHING_NUMBER")
    print("="*80 + "\n")
    
    odoo = OdooClient()
    
    # Buscar facturas de proveedores
    fecha_inicio = '2026-01-01'
    fecha_fin = '2026-02-28'
    
    facturas = odoo.search_read(
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
    
    print(f"Total facturas encontradas: {len(facturas)}")
    print(f"Período: {fecha_inicio} a {fecha_fin}\n")
    
    # Obtener líneas de todas las facturas
    factura_ids = [f['id'] for f in facturas]
    todas_lineas = odoo.search_read(
        'account.move.line',
        [['move_id', 'in', factura_ids]],
        ['id', 'move_id', 'matching_number', 'date', 'debit', 'credit'],
        limit=50000
    )
    
    print(f"Total líneas encontradas: {len(todas_lineas)}\n")
    
    # Agrupar líneas por factura
    lineas_por_factura = defaultdict(list)
    for linea in todas_lineas:
        move_id = linea.get('move_id')
        if isinstance(move_id, (list, tuple)):
            move_id = move_id[0]
        lineas_por_factura[move_id].append(linea)
    
    # Clasificar facturas
    categorias = {
        'PAGADAS_A': [],  # AXXXXX
        'PARCIALES_P': [],  # P
        'NO_PAGADAS': [],  # blank
        'OTROS': []  # Otros valores
    }
    
    for f in facturas:
        lineas = lineas_por_factura.get(f['id'], [])
        
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
        
        categorias[categoria].append({
            'id': f['id'],
            'name': f.get('name', ''),
            'matching_number': matching_number,
            'amount_total': f.get('amount_total', 0),
            'amount_residual': f.get('amount_residual', 0),
            'partner': f.get('partner_id', [0, 'Sin nombre'])[1] if isinstance(f.get('partner_id'), (list, tuple)) else 'Sin nombre',
            'move_type': f.get('move_type', '')
        })
    
    # Mostrar resumen
    print("="*80)
    print("RESUMEN POR CATEGORÍA")
    print("="*80 + "\n")
    
    for cat_name, facturas_cat in categorias.items():
        if not facturas_cat:
            continue
        
        total_monto = sum(f['amount_total'] for f in facturas_cat)
        total_residual = sum(f['amount_residual'] for f in facturas_cat)
        total_pagado = total_monto - total_residual
        
        print(f"\n📊 {cat_name}: {len(facturas_cat)} facturas")
        print("-" * 80)
        print(f"  Monto total:     {format_money(total_monto)}")
        print(f"  Residual total:  {format_money(total_residual)}")
        print(f"  Pagado total:    {format_money(total_pagado)}")
        
        # Ejemplos
        print(f"\n  Ejemplos (primeros 5):")
        for i, f in enumerate(facturas_cat[:5], 1):
            print(f"    {i}. {f['name']:20} | Match: {str(f['matching_number']):10} | Total: {format_money(f['amount_total']):>20} | Residual: {format_money(f['amount_residual']):>20} | {f['partner'][:30]}")
    
    print("\n" + "="*80)
    print("VALIDACIÓN DE TOTALES")
    print("="*80)
    
    total_facturas = sum(len(facturas_cat) for facturas_cat in categorias.values())
    print(f"\nTotal facturas clasificadas: {total_facturas}")
    print(f"Total facturas original:     {len(facturas)}")
    
    if total_facturas == len(facturas):
        print("✅ Todas las facturas fueron clasificadas")
    else:
        print(f"❌ Faltan {len(facturas) - total_facturas} facturas por clasificar")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
