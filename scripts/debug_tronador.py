"""
DEBUG: Traza completa de TRONADOR SAC en Flujo de Caja 1.1.1
Muestra facturas, montos, estados de pago, y cómo se distribuyen por semana.

Ejecutar: python scripts/debug_tronador.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from shared.odoo_client import OdooClient

# Tasa hardcodeada (la misma que usa el sistema hoy)
USD_CLP_RATE = 950.0  # fallback rate

# Credenciales
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"
FECHA_INICIO = "2026-01-01"
FECHA_FIN = "2026-04-30"

odoo = OdooClient(username=USERNAME, password=PASSWORD)

def iso_week(fecha_str):
    """Convierte fecha a semana ISO (2026-W04)"""
    try:
        dt = datetime.strptime(str(fecha_str)[:10], '%Y-%m-%d')
        y, w, d = dt.isocalendar()
        return f"{y}-W{w:02d}"
    except:
        return "???"

def fmt(n):
    """Formatea número con separador de miles"""
    if n == 0:
        return "$0"
    return f"${n:,.0f}"

def fmt_usd(n):
    """Formatea USD"""
    return f"USD {n:,.2f}"

print("=" * 120)
print("DEBUG TRONADOR SAC - Flujo de Caja 1.1.1")
print(f"Período: {FECHA_INICIO} a {FECHA_FIN}")
print("=" * 120)

# ============================================================
# PARTE 1: Datos de real_proyectado.py (calcular_cobros_clientes)
# Esta es la función que REEMPLAZA los datos del agregador para 1.1.1
# ============================================================
print("\n" + "=" * 120)
print("PARTE 1: REAL_PROYECTADO - calcular_cobros_clientes()")
print("Consulta: account.move con move_type=out_invoice, state=posted, invoice_date en rango")
print("=" * 120)

facturas_rp = odoo.search_read(
    'account.move',
    [
        ['move_type', '=', 'out_invoice'],
        ['state', '=', 'posted'],
        ['invoice_date', '>=', FECHA_INICIO],
        ['invoice_date', '<=', FECHA_FIN],
        ['payment_state', '!=', 'reversed']
    ],
    ['id', 'name', 'partner_id', 'invoice_date', 'invoice_date_due',
     'amount_total', 'amount_residual', 'payment_state', 'x_studio_fecha_estimada_de_pago',
     'x_studio_fecha_de_pago', 'currency_id'],
    limit=5000
)

# Filtrar TRONADOR
tronador_rp = [f for f in facturas_rp if 'TRONADOR' in str(f.get('partner_id', '')).upper()]

print(f"\nTotal facturas en rango: {len(facturas_rp)}")
print(f"Facturas de TRONADOR: {len(tronador_rp)}")

# Obtener tasa USD/CLP
try:
    import requests
    resp = requests.get("https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx?user=mvalladares@riofuturo.cl&pass=Rv240741&timeseries=F073.TCO.PRE.Z.D&firstdate=2026-02-20&lastdate=2026-02-24", timeout=10)
    data = resp.json()
    series = data.get('Series', {}).get('Obs', [])
    if series:
        rate = float(series[-1].get('value', USD_CLP_RATE))
    else:
        rate = USD_CLP_RATE
except:
    rate = USD_CLP_RATE
print(f"Tasa USD/CLP: {rate}")

print(f"\n{'─' * 120}")
print(f"{'FACTURA':<18} {'FECHA_FAC':<12} {'FECHA_PAGO':<12} {'FECHA_EST':<12} {'MONEDA':<6} "
      f"{'TOTAL_ORIG':>14} {'RESID_ORIG':>14} {'TOTAL_CLP':>16} {'RESID_CLP':>16} "
      f"{'COBRADO_CLP':>16} {'ESTADO':<12} {'SEM_REAL':<10} {'SEM_PROY':<10}")
print(f"{'─' * 120}")

total_cobrado_rp = 0
total_pendiente_rp = 0
por_estado_rp = {}
por_semana_rp = {}

for f in sorted(tronador_rp, key=lambda x: x.get('invoice_date', '')):
    name = f['name']
    fecha_fac = f.get('invoice_date', '')
    fecha_pago = f.get('x_studio_fecha_de_pago', '') or ''
    fecha_est = f.get('x_studio_fecha_estimada_de_pago', '') or ''
    fecha_due = f.get('invoice_date_due', '') or ''
    
    currency_data = f.get('currency_id')
    currency = currency_data[1] if isinstance(currency_data, (list, tuple)) and len(currency_data) > 1 else 'CLP'
    is_usd = 'USD' in str(currency).upper()
    
    amount_total_orig = f.get('amount_total', 0) or 0
    amount_residual_orig = f.get('amount_residual', 0) or 0
    
    # Convertir a CLP
    if is_usd:
        amount_total_clp = amount_total_orig * rate
        amount_residual_clp = amount_residual_orig * rate
    else:
        amount_total_clp = amount_total_orig
        amount_residual_clp = amount_residual_orig
    
    cobrado_clp = amount_total_clp - amount_residual_clp
    payment_state = f.get('payment_state', 'not_paid')
    
    sem_real = iso_week(fecha_fac)
    
    # Período proyectado
    if fecha_est:
        sem_proy = iso_week(str(fecha_est)[:10])
    elif fecha_due:
        sem_proy = iso_week(str(fecha_due)[:10])
    else:
        sem_proy = sem_real
    
    print(f"{name:<18} {str(fecha_fac):<12} {str(fecha_pago):<12} {str(fecha_est)[:10] if fecha_est else '':>12} "
          f"{currency:<6} {fmt_usd(amount_total_orig):>14} {fmt_usd(amount_residual_orig):>14} "
          f"{fmt(amount_total_clp):>16} {fmt(amount_residual_clp):>16} "
          f"{fmt(cobrado_clp):>16} {payment_state:<12} {sem_real:<10} {sem_proy:<10}")
    
    total_cobrado_rp += cobrado_clp
    total_pendiente_rp += amount_residual_clp
    
    # Acumular por estado
    if payment_state not in por_estado_rp:
        por_estado_rp[payment_state] = {'cobrado': 0, 'pendiente': 0, 'facturas': []}
    por_estado_rp[payment_state]['cobrado'] += cobrado_clp
    por_estado_rp[payment_state]['pendiente'] += amount_residual_clp
    por_estado_rp[payment_state]['facturas'].append(name)
    
    # Acumular por semana (lógica de real_proyectado)
    # Para paid: todo cobrado en periodo_real
    # Para partial: cobrado en periodo_real (Parciales), pendiente en periodo_proyectado (Parciales)
    # Para not_paid: todo en periodo_proyectado (No Pagadas)
    if payment_state == 'paid':
        key = ('paid', sem_real)
        por_semana_rp[key] = por_semana_rp.get(key, 0) + cobrado_clp
    elif payment_state == 'partial':
        if cobrado_clp > 0:
            key = ('partial_cobrado', sem_real)
            por_semana_rp[key] = por_semana_rp.get(key, 0) + cobrado_clp
        if amount_residual_clp > 0:
            key = ('partial_pendiente', sem_proy)
            por_semana_rp[key] = por_semana_rp.get(key, 0) + amount_residual_clp
    elif payment_state == 'not_paid':
        key = ('not_paid', sem_proy)
        por_semana_rp[key] = por_semana_rp.get(key, 0) + (cobrado_clp + amount_residual_clp)

print(f"{'─' * 120}")
print(f"\nRESUMEN POR ESTADO (real_proyectado):")
for estado, data in sorted(por_estado_rp.items()):
    print(f"  {estado}: cobrado={fmt(data['cobrado'])}, pendiente={fmt(data['pendiente'])}, "
          f"total={fmt(data['cobrado'] + data['pendiente'])}, facturas={len(data['facturas'])}")

print(f"\n  TOTAL COBRADO: {fmt(total_cobrado_rp)}")
print(f"  TOTAL PENDIENTE: {fmt(total_pendiente_rp)}")
print(f"  SUMA: {fmt(total_cobrado_rp + total_pendiente_rp)}")

print(f"\nDISTRIBUCIÓN POR SEMANA (real_proyectado - POST FIX):")
print(f"  {'TIPO':<25} {'SEMANA':<12} {'MONTO':>16}")
for (tipo, sem), monto in sorted(por_semana_rp.items(), key=lambda x: x[0][1]):
    destino = {
        'paid': '→ Pagadas (real)',
        'partial_cobrado': '→ Parciales (real)',
        'partial_pendiente': '→ Parciales (proy)',
        'not_paid': '→ No Pagadas (proy)'
    }.get(tipo, tipo)
    print(f"  {destino:<25} {sem:<12} {fmt(monto):>16}")

# Totalizar por destino final
print(f"\nTOTAL POR DESTINO FINAL:")
destinos = {}
for (tipo, sem), monto in por_semana_rp.items():
    if tipo == 'paid':
        d = 'Facturas Pagadas'
    elif tipo in ('partial_cobrado', 'partial_pendiente'):
        d = 'Parcialmente Pagadas'
    elif tipo == 'not_paid':
        d = 'No Pagadas'
    else:
        d = tipo
    destinos[d] = destinos.get(d, 0) + monto

for d, m in sorted(destinos.items()):
    print(f"  {d}: {fmt(m)}")

# ============================================================
# PARTE 2: Datos del agregador (odoo_queries.py)
# Esta es la consulta que el agregador hace con x_studio_fecha_de_pago
# ============================================================
print("\n\n" + "=" * 120)
print("PARTE 2: AGREGADOR - odoo_queries.get_lineas_cuenta_periodo()")
print("Consulta: account.move con x_studio_fecha_de_pago en rango O date en rango")
print("=" * 120)

domain_moves = [
    ['move_type', 'in', ['out_invoice', 'out_refund']],
    ['state', '=', 'posted'],
    '|',
    '&', '&',
        ['x_studio_fecha_de_pago', '!=', False],
        ['x_studio_fecha_de_pago', '>=', FECHA_INICIO],
        ['x_studio_fecha_de_pago', '<=', FECHA_FIN],
    '&', '&',
        ['x_studio_fecha_de_pago', '=', False],
        ['date', '>=', FECHA_INICIO],
        ['date', '<=', FECHA_FIN],
]

moves_agg = odoo.search_read(
    'account.move',
    domain_moves,
    ['id', 'name', 'x_studio_fecha_de_pago', 'date', 'move_type', 'state', 
     'payment_state', 'partner_id', 'amount_total', 'amount_residual']
)

tronador_agg = [m for m in moves_agg if 'TRONADOR' in str(m.get('partner_id', '')).upper()]

print(f"\nTotal moves en rango: {len(moves_agg)}")
print(f"Moves TRONADOR: {len(tronador_agg)}")

print(f"\n{'─' * 120}")
print(f"{'FACTURA':<18} {'TIPO':<12} {'FECHA_PAGO':<12} {'FECHA_CONT':<12} {'FECHA_EF':<12} "
      f"{'PAYMENT_ST':<12} {'TOTAL':>14} {'RESIDUAL':>14} {'SEM_EF':<10}")
print(f"{'─' * 120}")

for m in sorted(tronador_agg, key=lambda x: x.get('x_studio_fecha_de_pago') or x.get('date', '')):
    name = m['name']
    fecha_pago = m.get('x_studio_fecha_de_pago', '') or ''
    fecha_cont = m.get('date', '') or ''
    fecha_ef = fecha_pago if fecha_pago else fecha_cont
    sem_ef = iso_week(fecha_ef)
    
    print(f"{name:<18} {m.get('move_type',''):<12} {str(fecha_pago):<12} {str(fecha_cont):<12} "
          f"{str(fecha_ef):<12} {m.get('payment_state',''):<12} "
          f"{m.get('amount_total',0):>14,.2f} {m.get('amount_residual',0):>14,.2f} {sem_ef:<10}")

# Ahora buscar las líneas contables de esos moves en la cuenta 11030101
print(f"\n{'─' * 120}")
print("LÍNEAS CONTABLES (account.move.line) en cuenta 11030101:")

# Obtener ID de cuenta 11030101
cuentas = odoo.search_read('account.account', [['code', '=', '11030101']], ['id', 'code'])
if cuentas:
    cuenta_id = cuentas[0]['id']
    
    move_ids_tronador = [m['id'] for m in tronador_agg]
    if move_ids_tronador:
        lineas = odoo.search_read(
            'account.move.line',
            [['account_id', '=', cuenta_id], ['move_id', 'in', move_ids_tronador]],
            ['move_id', 'name', 'balance', 'date', 'account_id'],
            limit=500
        )
        
        # Crear lookup de move info
        move_lookup = {m['id']: m for m in tronador_agg}
        
        print(f"\n{'FACTURA':<18} {'BALANCE_CLP':>16} {'PAYMENT_ST':<12} {'TOTAL_INV':>14} {'RESID_INV':>14} "
              f"{'RATIO':>8} {'MONTO_EF':>16} {'MONTO_PAG':>16} {'SEM_EF':<10}")
        print(f"{'─' * 120}")
        
        total_balance = 0
        total_monto_ef = 0
        total_monto_pag = 0
        
        por_semana_agg = {}
        
        for l in sorted(lineas, key=lambda x: (x.get('move_id', [0, ''])[1] if isinstance(x.get('move_id'), (list, tuple)) else '')):
            move_data = l.get('move_id', [0, ''])
            move_id = move_data[0] if isinstance(move_data, (list, tuple)) else move_data
            move_name = move_data[1] if isinstance(move_data, (list, tuple)) and len(move_data) > 1 else '?'
            
            m_info = move_lookup.get(move_id, {})
            payment_state = m_info.get('payment_state', 'not_paid')
            amount_total = float(m_info.get('amount_total') or 0)
            amount_residual = float(m_info.get('amount_residual') or 0)
            balance = l.get('balance', 0)
            
            fecha_ef = m_info.get('x_studio_fecha_de_pago') or m_info.get('date', '')
            sem_ef = iso_week(fecha_ef)
            
            # Lógica del agregador
            monto_efectivo = balance
            monto_pagado_parcial = 0.0
            if payment_state == 'partial' and amount_total > 0:
                residual_ratio = amount_residual / amount_total
                monto_residual = balance * residual_ratio
                monto_pagado_parcial = balance - monto_residual
                monto_efectivo = monto_residual
            
            ratio = amount_residual / amount_total if amount_total > 0 else 0
            
            print(f"{move_name:<18} {fmt(balance):>16} {payment_state:<12} "
                  f"{amount_total:>14,.2f} {amount_residual:>14,.2f} "
                  f"{ratio:>8.4f} {fmt(monto_efectivo):>16} {fmt(monto_pagado_parcial):>16} {sem_ef:<10}")
            
            total_balance += balance
            total_monto_ef += monto_efectivo
            total_monto_pag += monto_pagado_parcial
            
            # Parciales → monto_efectivo a Parciales, monto_pagado_parcial a Pagadas
            # Pagadas → todo a Pagadas
            # No pagadas → todo a No Pagadas
            estado_label = {'paid': 'Pagadas', 'partial': 'Parciales', 'not_paid': 'No Pagadas', 'in_payment': 'En Proceso'}.get(payment_state, payment_state)
            key = (estado_label, sem_ef)
            por_semana_agg[key] = por_semana_agg.get(key, 0) + monto_efectivo
            if monto_pagado_parcial != 0:
                key2 = ('Pagadas (de parcial)', sem_ef)
                por_semana_agg[key2] = por_semana_agg.get(key2, 0) + monto_pagado_parcial
        
        print(f"{'─' * 120}")
        print(f"{'TOTALES':<18} {fmt(total_balance):>16} {'':12} {'':>14} {'':>14} "
              f"{'':>8} {fmt(total_monto_ef):>16} {fmt(total_monto_pag):>16}")
        
        print(f"\nDISTRIBUCIÓN POR SEMANA (agregador):")
        print(f"  {'DESTINO':<25} {'SEMANA':<12} {'MONTO':>16}")
        for (dest, sem), monto in sorted(por_semana_agg.items(), key=lambda x: x[0][1]):
            print(f"  {dest:<25} {sem:<12} {fmt(monto):>16}")
else:
    print("  ⚠ No se encontró cuenta 11030101")

# ============================================================
# PARTE 3: COMPARACIÓN
# ============================================================
print("\n\n" + "=" * 120)
print("PARTE 3: COMPARACIÓN - ¿Qué genera los datos finales?")
print("=" * 120)
print("""
IMPORTANTE: La función `enriquecer_concepto()` en flujo_caja_service.py REEMPLAZA 
los datos del agregador para 1.1.1 con los datos de `calcular_cobros_clientes()`.

Esto significa que los datos de la PARTE 1 (real_proyectado) son los que aparecen 
en el dashboard, NO los de la PARTE 2 (agregador).

Los criterios de fecha también son DIFERENTES:
- PARTE 1 (real_proyectado): usa invoice_date para filtrar
- PARTE 2 (agregador): usa x_studio_fecha_de_pago (o date como fallback) para filtrar

REGLA DE CLASIFICACIÓN POST-FIX:
- paid → Todo a "Facturas Pagadas" (REAL)
- partial → Cobrado a "Parcialmente Pagadas" (REAL) + Pendiente a "Parcialmente Pagadas" (PROYECTADO)
- not_paid → Todo a "Facturas No Pagadas" (PROYECTADO)
""")
