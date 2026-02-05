"""
Debug: Análisis completo para columnas REAL / PROYECTADO / PPTO
===============================================================

Este script analiza la estructura de datos para implementar:
1. REAL: Valores efectivamente realizados (pagados/cobrados)
2. PROYECTADO: Valores pendientes (adeudado)
3. PPTO: Presupuesto (vacío por ahora)

Para conceptos específicos:
- 1.2.1: Pagos a proveedores (diario Facturas de Proveedores)
- 1.2.6: IVA Exportador (cuenta 11060108 con partner Tesorería)
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

def analizar_pagos_proveedores(odoo, fecha_inicio, fecha_fin):
    """
    Analiza 1.2.1 - Pagos a proveedores
    
    REAL: Facturas pagadas (total o parcial pagado)
    PROYECTADO: Importe adeudado (residual de parciales + no pagadas)
    """
    print("\n" + "=" * 80)
    print("1.2.1 - PAGOS A PROVEEDORES POR SUMINISTRO DE BIENES Y SERVICIOS")
    print("=" * 80)
    
    # Buscar facturas de proveedor en el período
    facturas = odoo.search_read(
        'account.move',
        [
            ['move_type', 'in', ['in_invoice', 'in_refund']],
            ['date', '>=', fecha_inicio],
            ['date', '<=', fecha_fin],
            ['state', '=', 'posted']
        ],
        ['id', 'name', 'partner_id', 'date', 'amount_total', 'amount_residual', 
         'payment_state', 'move_type', 'journal_id'],
        limit=1000,
        order='date'
    )
    
    # Calcular REAL y PROYECTADO por mes
    por_mes = defaultdict(lambda: {'real': 0, 'proyectado': 0, 'facturas': []})
    
    for f in facturas:
        fecha = f.get('date', '')
        if not fecha:
            continue
        mes = fecha[:7]  # YYYY-MM
        
        amount_total = f.get('amount_total', 0)
        amount_residual = f.get('amount_residual', 0)
        payment_state = f.get('payment_state', '')
        move_type = f.get('move_type', '')
        
        # Nota de crédito invierte el signo
        signo = -1 if move_type == 'in_refund' else 1
        
        # REAL = lo efectivamente pagado
        pagado = (amount_total - amount_residual) * signo
        
        # PROYECTADO = lo que falta por pagar
        pendiente = amount_residual * signo
        
        por_mes[mes]['real'] += pagado
        por_mes[mes]['proyectado'] += pendiente
        por_mes[mes]['facturas'].append({
            'name': f['name'],
            'payment_state': payment_state,
            'total': amount_total,
            'pagado': pagado,
            'pendiente': pendiente
        })
    
    # Mostrar resultados
    print(f"\n{'Mes':<10} | {'REAL (Pagado)':>18} | {'PROYECTADO (Pend)':>18} | {'#Fact':>6}")
    print("-" * 60)
    
    total_real = 0
    total_proy = 0
    
    for mes in sorted(por_mes.keys()):
        data = por_mes[mes]
        total_real += data['real']
        total_proy += data['proyectado']
        print(f"{mes:<10} | ${data['real']:>16,.0f} | ${data['proyectado']:>16,.0f} | {len(data['facturas']):>6}")
    
    print("-" * 60)
    print(f"{'TOTAL':<10} | ${total_real:>16,.0f} | ${total_proy:>16,.0f}")
    
    return por_mes


def analizar_iva_exportador(odoo, fecha_inicio, fecha_fin):
    """
    Analiza 1.2.6 - IVA Exportador
    
    Solo cuenta 11060108 con partner "Tesorería General de la República"
    REAL: Créditos en la cuenta (devoluciones recibidas)
    """
    print("\n" + "=" * 80)
    print("1.2.6 - OTRAS ENTRADAS (SALIDAS) DE EFECTIVO - IVA EXPORTADOR")
    print("=" * 80)
    
    # IDs conocidos
    CUENTA_IVA_ID = 503  # 11060108 - DEVOLUCION IVA EXPORTADOR
    PARTNER_TESORERIA_ID = 10  # TESORERÍA GENERAL DE LA REPÚBLICA
    
    # Buscar movimientos
    movimientos = odoo.search_read(
        'account.move.line',
        [
            ['account_id', '=', CUENTA_IVA_ID],
            ['partner_id', '=', PARTNER_TESORERIA_ID],
            ['parent_state', '=', 'posted'],
            ['date', '>=', fecha_inicio],
            ['date', '<=', fecha_fin]
        ],
        ['id', 'move_id', 'date', 'name', 'debit', 'credit', 'balance'],
        limit=500,
        order='date'
    )
    
    # Agrupar por mes
    por_mes = defaultdict(lambda: {'real': 0, 'movimientos': []})
    
    for m in movimientos:
        fecha = m.get('date', '')
        if not fecha:
            continue
        mes = fecha[:7]
        
        # Para IVA Exportador, los CRÉDITOS son devoluciones recibidas (entrada de efectivo)
        # Entonces REAL = credit (entrada de dinero, positivo para el flujo)
        credit = m.get('credit', 0)
        
        por_mes[mes]['real'] += credit
        por_mes[mes]['movimientos'].append({
            'name': m.get('name', ''),
            'credit': credit,
            'date': fecha
        })
    
    # Mostrar resultados
    print(f"\n{'Mes':<10} | {'REAL (Devolucion)':>18} | {'PROYECTADO':>18} | {'#Mov':>6}")
    print("-" * 60)
    
    total_real = 0
    
    for mes in sorted(por_mes.keys()):
        data = por_mes[mes]
        total_real += data['real']
        print(f"{mes:<10} | ${data['real']:>16,.0f} | {'$0':>18} | {len(data['movimientos']):>6}")
    
    print("-" * 60)
    print(f"{'TOTAL':<10} | ${total_real:>16,.0f} | {'$0':>18}")
    
    # Detalle de movimientos
    print("\n  Detalle de devoluciones:")
    for mes in sorted(por_mes.keys()):
        for m in por_mes[mes]['movimientos']:
            print(f"    {m['date']} | ${m['credit']:>15,.0f} | {m['name'][:40]}")
    
    return por_mes


def analizar_estructura_columnas(odoo, fecha_inicio, fecha_fin):
    """
    Muestra cómo quedaría la estructura de columnas REAL/PROYECTADO/PPTO
    """
    print("\n" + "=" * 80)
    print("ESTRUCTURA PROPUESTA: REAL | PROYECTADO | PPTO | Meses...")
    print("=" * 80)
    
    # Generar meses del período
    from datetime import datetime
    dt_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
    dt_fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
    
    meses = []
    current = dt_inicio
    while current <= dt_fin:
        meses.append(current.strftime('%Y-%m'))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    print(f"\nColumnas: REAL | PROYECTADO | PPTO | {' | '.join(meses)}")
    print("\nDonde:")
    print("  - REAL = Suma de todos los meses (efectivamente realizado)")
    print("  - PROYECTADO = Importe adeudado (parciales + pendientes)")
    print("  - PPTO = Presupuesto (vacío por ahora)")
    print("  - Meses = Detalle mensual")
    
    return meses


def main():
    print("=" * 80)
    print("DEBUG: ESTRUCTURA COLUMNAS REAL/PROYECTADO/PPTO")
    print("=" * 80)
    
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    
    # Período de análisis: Enero 2026
    fecha_inicio = '2026-01-01'
    fecha_fin = '2026-01-31'
    
    print(f"\nPeríodo de análisis: {fecha_inicio} a {fecha_fin}")
    
    # 1. Estructura de columnas
    meses = analizar_estructura_columnas(odoo, fecha_inicio, fecha_fin)
    
    # 2. Pagos a proveedores
    pagos_prov = analizar_pagos_proveedores(odoo, fecha_inicio, fecha_fin)
    
    # 3. IVA Exportador
    iva_exp = analizar_iva_exportador(odoo, fecha_inicio, fecha_fin)
    
    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN PARA IMPLEMENTACIÓN")
    print("=" * 80)
    
    print("""
    ESTRUCTURA DE DATOS A AGREGAR:
    ------------------------------
    
    Cada concepto tendrá:
    {
        "id": "1.2.1",
        "nombre": "Pagos a proveedores...",
        "real": <suma efectivamente pagada>,
        "proyectado": <importe adeudado>,
        "ppto": 0,  // Por ahora vacío
        "montos_por_mes": {"2026-01": xxx, ...}  // Existente
    }
    
    LÓGICA DE CÁLCULO:
    ------------------
    
    1.2.1 (Pagos Proveedores):
    - Fuente: account.move con move_type in ['in_invoice', 'in_refund']
    - REAL = amount_total - amount_residual (por factura)
    - PROYECTADO = amount_residual (por factura)
    
    1.2.6 (IVA Exportador):
    - Fuente: account.move.line donde:
      * account_id = 503 (11060108)
      * partner_id = 10 (Tesorería)
    - REAL = credit (devoluciones recibidas)
    - PROYECTADO = 0 (o solicitudes pendientes si existen)
    
    COLUMNAS EN UI:
    ---------------
    | Concepto | REAL | PROYECTADO | PPTO | Ene | Feb | Mar | ... |
    
    IMPORTANTE: Las columnas REAL/PROYECTADO/PPTO van ANTES de los meses
    """)


if __name__ == "__main__":
    main()
