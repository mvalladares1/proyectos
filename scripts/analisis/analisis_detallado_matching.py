# -*- coding: utf-8 -*-
"""
Análisis DETALLADO de matching_number para validar lógica de negocio
antes de implementar en calcular_pagos_proveedores.
"""
import sys
import os
import io

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
print("ANALISIS DETALLADO: Matching Number - Validacion de Logica de Negocio")
print("="*100 + "\n")

# Buscar diario
diarios = odoo.search_read(
    'account.journal',
    [('type', '=', 'purchase'), ('name', 'ilike', 'Facturas de Proveedores')],
    ['id', 'name', 'code'],
    limit=1
)
DIARIO_ID = diarios[0]['id'] if diarios else 2

print(f"[INFO] Usando diario ID: {DIARIO_ID} - {diarios[0]['name']}\n")

# Buscar facturas recientes posteadas
facturas = odoo.search_read(
    'account.move',
    [
        ('move_type', 'in', ['in_invoice', 'in_refund']),
        ('journal_id', '=', DIARIO_ID),
        ('state', '=', 'posted'),
        ('date', '>=', '2025-11-01')
    ],
    ['id', 'name', 'partner_id', 'date', 'invoice_date', 'amount_total', 
     'amount_residual', 'payment_state', 'move_type'],
    limit=200,
    order='date desc'
)

print(f"[INFO] Encontradas {len(facturas)} facturas para analizar\n")

# Clasificar facturas por matching_number
facturas_con_info = []

for f in facturas:
    # Buscar líneas de la factura
    lineas = odoo.search_read(
        'account.move.line',
        [('move_id', '=', f['id'])],
        ['id', 'account_id', 'debit', 'credit', 'matching_number', 'date', 'name'],
        limit=100
    )
    
    # Encontrar matching_number
    matching_number = None
    for linea in lineas:
        match = linea.get('matching_number')
        if match and match not in ['False', False, '', None]:
            matching_number = match
            break
    
    facturas_con_info.append({
        'factura': f,
        'matching': matching_number,
        'lineas': lineas
    })

# Separar por categoría
pagadas = [x for x in facturas_con_info if x['matching'] and x['matching'].startswith('A')]
parciales = [x for x in facturas_con_info if x['matching'] == 'P']
no_pagadas = [x for x in facturas_con_info if not x['matching']]
revertidas = [x for x in facturas_con_info if x['factura']['move_type'] == 'in_refund']

print("="*100)
print(f"RESUMEN DE CLASIFICACION")
print("="*100)
print(f"PAGADAS (AXXXXX):     {len(pagadas)} facturas")
print(f"PARCIALES (P):        {len(parciales)} facturas")
print(f"NO PAGADAS (blank):   {len(no_pagadas)} facturas")
print(f"REVERTIDAS (N/C):     {len(revertidas)} facturas")
print()

# ===========================================================================================
# CASO 1: FACTURAS PAGADAS (AXXXXX)
# ===========================================================================================
print("\n" + "="*100)
print("CASO 1: FACTURAS TOTALMENTE PAGADAS (Matching = AXXXXX)")
print("="*100)
print("\nLOGICA ESPERADA:")
print("- Buscar el matching_number (ej: A51062) en TODAS las lineas de account.move.line")
print("- Las lineas con ese matching conectan la factura con el pago")
print("- Linea con DEBITO > 0 = el pago real")
print("- Usar la FECHA de esa linea de pago")
print("- Agrupar por fecha del pago, sumar DEBITO de las lineas de pago\n")

if pagadas:
    # Tomar 3 ejemplos
    for i, info in enumerate(pagadas[:3], 1):
        f = info['factura']
        matching = info['matching']
        
        partner = f.get('partner_id', [0, ''])
        partner_name = partner[1] if isinstance(partner, (list, tuple)) else ''
        
        print(f"\n{'-'*100}")
        print(f"EJEMPLO {i}: Factura {f['name']} - {partner_name}")
        print(f"{'-'*100}")
        print(f"  Matching Number: {matching}")
        print(f"  Fecha Factura: {f.get('invoice_date', 'N/A')}")
        print(f"  Total: ${f['amount_total']:,.2f}")
        print(f"  Residual: ${f['amount_residual']:,.2f}")
        print(f"  Payment State: {f['payment_state']}")
        
        # Buscar TODAS las líneas con este matching_number
        print(f"\n  Buscando TODAS las lineas con matching = '{matching}'...")
        lineas_matching = odoo.search_read(
            'account.move.line',
            [('matching_number', '=', matching)],
            ['id', 'move_id', 'account_id', 'debit', 'credit', 'date', 'name'],
            limit=50
        )
        
        print(f"  Encontradas {len(lineas_matching)} lineas:\n")
        
        for linea in lineas_matching:
            cuenta = linea.get('account_id', [0, ''])
            cuenta_str = cuenta[1] if isinstance(cuenta, (list, tuple)) else ''
            move = linea.get('move_id', [0, ''])
            move_str = move[1] if isinstance(move, (list, tuple)) else ''
            
            tipo_linea = ""
            if linea['debit'] > 0:
                tipo_linea = " <-- PAGO (usar esta fecha)"
            elif linea['credit'] > 0:
                tipo_linea = " <-- FACTURA (credit)"
            
            print(f"    * {move_str}")
            print(f"      Fecha: {linea['date']} | Cuenta: {cuenta_str}")
            print(f"      Debito: ${linea['debit']:,.2f} | Credito: ${linea['credit']:,.2f}{tipo_linea}")
            print()
        
        # VALIDACION: ¿Qué fecha debemos usar?
        lineas_pago = [l for l in lineas_matching if l['debit'] > 0]
        if lineas_pago:
            fecha_pago = lineas_pago[0]['date']
            total_debito = sum(l['debit'] for l in lineas_pago)
            print(f"  [VALIDACION] Fecha a usar: {fecha_pago}")
            print(f"  [VALIDACION] Monto a registrar: ${total_debito:,.2f}")
        else:
            print(f"  [ALERTA] No se encontro linea con debito > 0!")

else:
    print("\n[INFO] No hay facturas pagadas en la muestra")

# ===========================================================================================
# CASO 2: FACTURAS PARCIALMENTE PAGADAS (P)
# ===========================================================================================
print("\n\n" + "="*100)
print("CASO 2: FACTURAS PARCIALMENTE PAGADAS (Matching = P)")
print("="*100)
print("\nLOGICA ESPERADA:")
print("- Multiples lineas pueden tener matching = 'P'")
print("- Para cada factura: SUMA(DEBITOS) - SUMA(CREDITOS) de lineas con 'P'")
print("- Lo que da positivo = Ya pagado")
print("- amount_residual = Pendiente de pagar")
print("- Fecha: ¿Usar invoice_date o date de las lineas con debito?\n")

if parciales:
    # Tomar 3 ejemplos
    for i, info in enumerate(parciales[:3], 1):
        f = info['factura']
        lineas = info['lineas']
        
        partner = f.get('partner_id', [0, ''])
        partner_name = partner[1] if isinstance(partner, (list, tuple)) else ''
        
        print(f"\n{'-'*100}")
        print(f"EJEMPLO {i}: Factura {f['name']} - {partner_name}")
        print(f"{'-'*100}")
        print(f"  Fecha Factura: {f.get('invoice_date', 'N/A')}")
        print(f"  Total Factura: ${f['amount_total']:,.2f}")
        print(f"  Residual (por pagar): ${f['amount_residual']:,.2f}")
        print(f"  Ya pagado: ${f['amount_total'] - f['amount_residual']:,.2f}")
        print(f"  Payment State: {f['payment_state']}")
        
        # Filtrar líneas con matching = P
        lineas_p = [l for l in lineas if l.get('matching_number') == 'P']
        
        print(f"\n  Lineas con matching = 'P': {len(lineas_p)}")
        
        total_debito_p = 0
        total_credito_p = 0
        
        for linea in lineas_p[:10]:  # Mostrar máximo 10
            cuenta = linea.get('account_id', [0, ''])
            cuenta_str = cuenta[1] if isinstance(cuenta, (list, tuple)) else ''
            
            total_debito_p += linea['debit']
            total_credito_p += linea['credit']
            
            print(f"    * {linea.get('name', 'Sin descripcion')[:60]}")
            print(f"      Cuenta: {cuenta_str}")
            print(f"      Debito: ${linea['debit']:,.2f} | Credito: ${linea['credit']:,.2f}")
        
        if len(lineas_p) > 10:
            print(f"    ... ({len(lineas_p) - 10} lineas mas)")
        
        diferencia = total_debito_p - total_credito_p
        
        print(f"\n  [CALCULO] Suma Debitos con 'P': ${total_debito_p:,.2f}")
        print(f"  [CALCULO] Suma Creditos con 'P': ${total_credito_p:,.2f}")
        print(f"  [CALCULO] Diferencia (Deb-Cred): ${diferencia:,.2f}")
        print(f"  [VALIDACION] Monto ya pagado (amount_total - residual): ${f['amount_total'] - f['amount_residual']:,.2f}")
        print(f"  [VALIDACION] Pendiente por pagar (residual): ${f['amount_residual']:,.2f}")

else:
    print("\n[INFO] No hay facturas parciales en la muestra")

# ===========================================================================================
# CASO 3: FACTURAS NO PAGADAS (blank)
# ===========================================================================================
print("\n\n" + "="*100)
print("CASO 3: FACTURAS NO PAGADAS (Matching = blank)")
print("="*100)
print("\nLOGICA ESPERADA:")
print("- No tienen matching_number (blank o None)")
print("- Usar invoice_date + 30 dias para proyectar el pago")
print("- Todo el monto va a PROYECTADO (no hay REAL)")
print("- Monto = amount_total (negativo porque es salida)\n")

if no_pagadas:
    # Tomar 3 ejemplos con monto > 0
    ejemplos = [x for x in no_pagadas if x['factura']['amount_total'] > 0][:3]
    
    for i, info in enumerate(ejemplos, 1):
        f = info['factura']
        
        partner = f.get('partner_id', [0, ''])
        partner_name = partner[1] if isinstance(partner, (list, tuple)) else ''
        
        invoice_date = f.get('invoice_date')
        fecha_proyectada = None
        if invoice_date:
            try:
                fecha_dt = datetime.strptime(invoice_date, '%Y-%m-%d')
                fecha_proyectada = (fecha_dt + timedelta(days=30)).strftime('%Y-%m-%d')
            except:
                pass
        
        print(f"\n{'-'*100}")
        print(f"EJEMPLO {i}: Factura {f['name']} - {partner_name}")
        print(f"{'-'*100}")
        print(f"  Invoice Date: {invoice_date}")
        print(f"  Total: ${f['amount_total']:,.2f}")
        print(f"  Residual: ${f['amount_residual']:,.2f}")
        print(f"  Payment State: {f['payment_state']}")
        print(f"\n  [VALIDACION] Fecha proyectada (invoice_date + 30): {fecha_proyectada}")
        print(f"  [VALIDACION] Monto PROYECTADO: ${f['amount_total']:,.2f}")
        print(f"  [VALIDACION] Monto REAL: $0.00")

else:
    print("\n[INFO] No hay facturas no pagadas en la muestra")

# ===========================================================================================
# CASO 4: FACTURAS REVERTIDAS (Notas de Crédito)
# ===========================================================================================
print("\n\n" + "="*100)
print("CASO 4: FACTURAS REVERTIDAS (Notas de Credito)")
print("="*100)
print("\nLOGICA ESPERADA:")
print("- move_type = 'in_refund'")
print("- Se deben RESTAR del total (signo negativo invertido)")
print("- Pueden tener cualquier matching_number\n")

if revertidas:
    for i, info in enumerate(revertidas[:3], 1):
        f = info['factura']
        matching = info['matching']
        
        partner = f.get('partner_id', [0, ''])
        partner_name = partner[1] if isinstance(partner, (list, tuple)) else ''
        
        print(f"\n{'-'*100}")
        print(f"EJEMPLO {i}: N/C {f['name']} - {partner_name}")
        print(f"{'-'*100}")
        print(f"  Fecha: {f.get('date', 'N/A')}")
        print(f"  Total: ${f['amount_total']:,.2f}")
        print(f"  Residual: ${f['amount_residual']:,.2f}")
        print(f"  Matching: {matching if matching else '(blank)'}")
        print(f"  Payment State: {f['payment_state']}")
        print(f"\n  [VALIDACION] Como es N/C, el monto se RESTA del flujo")
        print(f"  [VALIDACION] Signo a aplicar: -1 (invertir)")

else:
    print("\n[INFO] No hay facturas revertidas en la muestra")

# ===========================================================================================
# RESUMEN FINAL
# ===========================================================================================
print("\n\n" + "="*100)
print("RESUMEN FINAL - PROPUESTA DE IMPLEMENTACION")
print("="*100)

print("""
1. FILTRO INICIAL:
   - journal_id = 2 (Facturas de Proveedores)
   - state = 'posted'
   - Incluir in_invoice e in_refund

2. CLASIFICACION POR MATCHING_NUMBER:
   
   a) PAGADO (AXXXXX):
      - Buscar todas las lineas con ese matching_number
      - Fecha = date de la linea con debit > 0
      - Monto REAL = -SUM(debit de lineas de pago)
      - Monto PROYECTADO = 0
      - Agrupar por: Estado "Pagadas" > Proveedor > Date
   
   b) PARCIAL (P):
      - Monto REAL = -(amount_total - amount_residual)
      - Monto PROYECTADO = -amount_residual
      - Fecha REAL = ¿invoice_date o buscar fecha de pagos parciales?
      - Fecha PROYECTADO = invoice_date + 30
      - Agrupar por: Estado "Parciales" > Proveedor
   
   c) NO PAGADO (blank):
      - Monto REAL = 0
      - Monto PROYECTADO = -amount_total
      - Fecha = invoice_date + 30
      - Agrupar por: Estado "No Pagadas" > Proveedor
   
   d) REVERTIDAS (in_refund):
      - Aplicar signo inverso: +amount_total
      - Clasificar según su matching (puede ser AXXXXX, P, o blank)

3. ESTRUCTURA JERARQUICA:
   - Nivel 2: Por estado (Pagadas, Parciales, No Pagadas)
   - Nivel 3: Por proveedor
   - Detalles: Lista de facturas con drill-down

4. CUENTAS A CONSIDERAR:
   - Buscar lineas con account.code LIKE '2102%' (Proveedores por Pagar)
   - Validar que las cuentas 2101% no son CxP de proveedores sino prestamos
""")

print("\n" + "="*100)
print("FIN DEL ANALISIS")
print("="*100)
print("\nREVISA los ejemplos arriba y confirma si la logica es correcta.")
print("Si todo esta bien, procedemos a implementar en calcular_pagos_proveedores().\n")
