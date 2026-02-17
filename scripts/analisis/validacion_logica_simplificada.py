# -*- coding: utf-8 -*-
"""
Validación de lógica SIMPLIFICADA para 1.2.1 - Pagos a Proveedores
usando amount_total - residual (más confiable).
"""
import sys
import os
import io
import json

# Configurar salida UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from shared.odoo_client import OdooClient
from datetime import datetime, timedelta

# Credenciales
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

odoo = OdooClient(username=USERNAME, password=PASSWORD)

print("\n" + "="*100)
print("VALIDACION DE LOGICA SIMPLIFICADA - Pagos a Proveedores (1.2.1)")
print("="*100 + "\n")

# Buscar diario
diarios = odoo.search_read(
    'account.journal',
    [('id', '=', 2)],
    ['id', 'name', 'code'],
    limit=1
)
DIARIO_ID = 2

print(f"Diario: {diarios[0]['name']} (ID: {DIARIO_ID})\n")

# Buscar facturas recientes
facturas = odoo.search_read(
    'account.move',
    [
        ('move_type', 'in', ['in_invoice', 'in_refund']),
        ('journal_id', '=', DIARIO_ID),
        ('state', '=', 'posted'),
        ('date', '>=', '2026-01-01'),
        ('date', '<=', '2026-02-15')
    ],
    ['id', 'name', 'partner_id', 'date', 'invoice_date', 'amount_total', 
     'amount_residual', 'payment_state', 'move_type'],
    limit=300,
    order='date desc'
)

print(f"Total facturas encontradas: {len(facturas)}\n")

# Analizar y clasificar
resultados = {
    'total_facturas': len(facturas),
    'facturas_por_matching': {},
    'ejemplos': [],
    'estadisticas': {
        'pagadas_axxxxx': 0,
        'parciales_p': 0,
        'no_pagadas_blank': 0,
        'revertidas': 0
    }
}

# Procesar cada factura
for f in facturas:
    # Buscar matching_number
    lineas = odoo.search_read(
        'account.move.line',
        [('move_id', '=', f['id'])],
        ['id', 'matching_number', 'date', 'account_id', 'debit', 'credit'],
        limit=100
    )
    
    matching_number = None
    for linea in lineas:
        match = linea.get('matching_number')
        if match and match not in ['False', False, '', None]:
            matching_number = match
            break
    
    # Clasificar
    move_type = f.get('move_type', '')
    is_refund = move_type == 'in_refund'
    
    if matching_number and matching_number.startswith('A'):
        categoria = 'PAGADAS_AXXXXX'
    elif matching_number == 'P':
        categoria = 'PARCIALES_P'
    elif not matching_number:
        categoria = 'NO_PAGADAS_BLANK'
    else:
        categoria = 'OTROS'
    
    if is_refund:
        resultados['estadisticas']['revertidas'] += 1
    
    # Calcular REAL y PROYECTADO usando lógica simplificada
    amount_total = f.get('amount_total', 0) or 0
    amount_residual = f.get('amount_residual', 0) or 0
    
    # Signo: Notas de crédito invierten el signo
    signo = -1 if is_refund else 1
    
    # LOGICA SIMPLIFICADA:
    # REAL = lo que ya se pagó (negativo porque es salida)
    monto_real = -(amount_total - amount_residual) * signo
    
    # PROYECTADO = lo que falta por pagar (negativo porque es salida)
    monto_proyectado = -amount_residual * signo
    
    # Para facturas PAGADAS con AXXXXX, buscar fecha de pago
    fecha_para_real = f.get('date', '')
    fecha_para_proyectado = None
    
    if categoria == 'PAGADAS_AXXXXX' and matching_number:
        # Buscar líneas con este matching para obtener fecha de pago
        lineas_matching = odoo.search_read(
            'account.move.line',
            [('matching_number', '=', matching_number)],
            ['id', 'move_id', 'date', 'debit', 'credit'],
            limit=10
        )
        
        # Buscar la línea de pago (con débito > 0)
        for lm in lineas_matching:
            if lm.get('debit', 0) > 0:
                fecha_para_real = lm.get('date', fecha_para_real)
                break
    
    # Para NO PAGADAS y PARCIALES, calcular fecha proyectada
    if categoria in ['NO_PAGADAS_BLANK', 'PARCIALES_P']:
        invoice_date = f.get('invoice_date')
        if invoice_date:
            try:
                fecha_dt = datetime.strptime(invoice_date, '%Y-%m-%d')
                fecha_proyectada = (fecha_dt + timedelta(days=30)).strftime('%Y-%m-%d')
                fecha_para_proyectado = fecha_proyectada
            except:
                pass
    
    if categoria not in resultados['facturas_por_matching']:
        resultados['facturas_por_matching'][categoria] = []
    
    resultados['facturas_por_matching'][categoria].append({
        'name': f['name'],
        'partner': f.get('partner_id', [0, ''])[1] if isinstance(f.get('partner_id'), (list, tuple)) else '',
        'move_type': move_type,
        'matching': matching_number,
        'amount_total': amount_total,
        'amount_residual': amount_residual,
        'monto_real': monto_real,
        'monto_proyectado': monto_proyectado,
        'fecha_factura': f.get('date', ''),
        'invoice_date': f.get('invoice_date', ''),
        'fecha_para_real': fecha_para_real,
        'fecha_para_proyectado': fecha_para_proyectado,
        'payment_state': f.get('payment_state', '')
    })
    
    # Contar estadísticas
    if categoria == 'PAGADAS_AXXXXX':
        resultados['estadisticas']['pagadas_axxxxx'] += 1
    elif categoria == 'PARCIALES_P':
        resultados['estadisticas']['parciales_p'] += 1
    elif categoria == 'NO_PAGADAS_BLANK':
        resultados['estadisticas']['no_pagadas_blank'] += 1

# Mostrar estadísticas
print("="*100)
print("ESTADISTICAS")
print("="*100)
print(f"Facturas PAGADAS (AXXXXX):     {resultados['estadisticas']['pagadas_axxxxx']}")
print(f"Facturas PARCIALES (P):        {resultados['estadisticas']['parciales_p']}")
print(f"Facturas NO PAGADAS (blank):   {resultados['estadisticas']['no_pagadas_blank']}")
print(f"Facturas REVERTIDAS (N/C):     {resultados['estadisticas']['revertidas']}")
print()

# Mostrar ejemplos por categoría
print("="*100)
print("EJEMPLOS POR CATEGORIA")
print("="*100)

for categoria, facturas_cat in resultados['facturas_por_matching'].items():
    print(f"\n{'='*100}")
    print(f"{categoria}: {len(facturas_cat)} facturas")
    print('='*100)
    
    # Tomar 3 ejemplos
    for i, fac in enumerate(facturas_cat[:3], 1):
        print(f"\n  EJEMPLO {i}: {fac['name']} - {fac['partner'][:50]}")
        print(f"  {'-'*96}")
        print(f"  Tipo: {fac['move_type']} | Matching: {fac['matching'] or '(blank)'}")
        print(f"  Amount Total: ${fac['amount_total']:,.2f}")
        print(f"  Amount Residual: ${fac['amount_residual']:,.2f}")
        print(f"  Payment State: {fac['payment_state']}")
        print()
        print(f"  CALCULOS:")
        print(f"  - Ya pagado (total - residual): ${fac['amount_total'] - fac['amount_residual']:,.2f}")
        print(f"  - Pendiente (residual): ${fac['amount_residual']:,.2f}")
        print()
        print(f"  RESULTADO:")
        print(f"  - Monto REAL (salida): ${fac['monto_real']:,.2f}")
        print(f"  - Monto PROYECTADO (salida): ${fac['monto_proyectado']:,.2f}")
        print(f"  - Fecha para REAL: {fac['fecha_para_real']}")
        print(f"  - Fecha para PROYECTADO: {fac['fecha_para_proyectado'] or 'N/A'}")
        print()

# Generar resumen en JSON para análisis externo
resumen_para_ia = {
    "contexto": {
        "concepto": "1.2.1 - Pagos a Proveedores",
        "diario": "Facturas de Proveedores (ID: 2)",
        "periodo_analizado": "2026-01-01 a 2026-02-15",
        "total_facturas": resultados['total_facturas']
    },
    "estadisticas": resultados['estadisticas'],
    "logica_implementada": {
        "descripcion": "Clasificación por matching_number con cálculo simplificado",
        "reglas": {
            "PAGADAS_AXXXXX": {
                "filtro": "matching_number empieza con 'A'",
                "calculo_real": "-(amount_total - amount_residual) * signo",
                "calculo_proyectado": "-amount_residual * signo (debería ser 0)",
                "fecha_real": "Fecha de la línea de pago (debit > 0) con mismo matching",
                "fecha_proyectado": "N/A (ya está pagado)"
            },
            "PARCIALES_P": {
                "filtro": "matching_number = 'P'",
                "calculo_real": "-(amount_total - amount_residual) * signo",
                "calculo_proyectado": "-amount_residual * signo",
                "fecha_real": "date de la factura",
                "fecha_proyectado": "invoice_date + 30 días"
            },
            "NO_PAGADAS_BLANK": {
                "filtro": "matching_number vacío o None",
                "calculo_real": "0 (no hay pagos)",
                "calculo_proyectado": "-amount_total * signo",
                "fecha_real": "N/A",
                "fecha_proyectado": "invoice_date + 30 días"
            },
            "REVERTIDAS": {
                "filtro": "move_type = 'in_refund'",
                "accion": "Invertir signo (signo = -1)",
                "nota": "Se clasifican según su matching pero con signo invertido"
            }
        }
    },
    "ejemplos": {
        "pagadas": resultados['facturas_por_matching'].get('PAGADAS_AXXXXX', [])[:5],
        "parciales": resultados['facturas_por_matching'].get('PARCIALES_P', [])[:5],
        "no_pagadas": resultados['facturas_por_matching'].get('NO_PAGADAS_BLANK', [])[:5]
    }
}

print("\n" + "="*100)
print("RESUMEN JSON PARA ANALISIS EXTERNO")
print("="*100)
print(json.dumps(resumen_para_ia, indent=2, ensure_ascii=False))

print("\n" + "="*100)
print("FIN DE VALIDACION")
print("="*100)
print("\nEste output será enviado a Claude API para feedback y validación de la lógica.\n")
