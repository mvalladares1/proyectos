"""
Debug FOCALIZADO: Por que read_group no retorna cuentas de financiamiento?
Analiza un asiento especifico para trazar todo el flujo.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from xmlrpc import client as xmlrpc_client
from collections import defaultdict

# Conexion
url = "https://riofuturo.server98c6e.oerpondemand.net"
db = "riofuturo-master"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

common = xmlrpc_client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc_client.ServerProxy(f'{url}/xmlrpc/2/object')

def search_read(model, domain, fields, limit=10000, order=None):
    kwargs = {'fields': fields, 'limit': limit}
    if order:
        kwargs['order'] = order
    return models.execute_kw(db, uid, password, model, 'search_read', [domain], kwargs)

def read_group(model, domain, fields, groupby, limit=10000):
    return models.execute_kw(db, uid, password, model, 'read_group', [domain, fields, groupby], {'limit': limit})

CUENTAS_FIJAS_FINANCIAMIENTO = {
    "21010101": "3.0.2", "21010102": "3.0.2", "21010103": "3.0.2", "82010101": "3.0.2",
    "21010213": "3.0.1", "21010223": "3.0.1", "22010101": "3.0.1",
    "21030201": "3.1.1", "21030211": "3.1.1", "22020101": "3.1.1",
    "21010201": "3.1.4", "21010202": "3.1.4", "21010204": "3.1.4",
    "22010202": "3.1.4", "22010204": "3.1.4", "82010102": "3.1.4"
}

FECHA_INICIO = "2026-01-01"
FECHA_FIN = "2026-02-25"

print("=" * 80)
print("DIAGNOSTICO: Trazando flujo de financiamiento")
print("=" * 80)

# 1. Cuentas de efectivo
cuentas_efectivo = search_read('account.account', [['code', 'like', '1101%']], ['id', 'code', 'name'], limit=100)
cuentas_efectivo_2 = search_read('account.account', [['code', 'like', '1102%']], ['id', 'code', 'name'], limit=100)
cuentas_efectivo.extend(cuentas_efectivo_2)
codigos_especificos = ["10000000", "10000001"]
for cod in codigos_especificos:
    cuentas_esp = search_read('account.account', [['code', '=', cod]], ['id', 'code', 'name'], limit=1)
    for c in cuentas_esp:
        if c['id'] not in [x['id'] for x in cuentas_efectivo]:
            cuentas_efectivo.append(c)

cuentas_efectivo_ids = [c['id'] for c in cuentas_efectivo]
print(f"Cuentas de efectivo: {len(cuentas_efectivo)} cuentas")

# 2. Movimientos de efectivo
movimientos = search_read(
    'account.move.line',
    [['account_id', 'in', cuentas_efectivo_ids], ['date', '>=', FECHA_INICIO], ['date', '<=', FECHA_FIN], ['parent_state', '=', 'posted']],
    ['id', 'move_id', 'account_id', 'balance', 'date'],
    limit=50000
)
asientos_ids = list(set(m['move_id'][0] for m in movimientos if m.get('move_id')))
print(f"Movimientos de efectivo: {len(movimientos)}, Asientos unicos: {len(asientos_ids)}")

# 3. DIAGNOSTICO CLAVE: Veamos que retorna read_group para estos asientos
print(f"\n{'='*80}")
print("DIAGNOSTICO 1: read_group de contrapartidas (como hace el dashboard)")
print(f"{'='*80}")

grupos = read_group(
    'account.move.line',
    [['move_id', 'in', asientos_ids], ['account_id', 'not in', cuentas_efectivo_ids], ['parent_state', '=', 'posted']],
    ['account_id', 'balance', 'date'],
    ['account_id', 'date:month'],
    limit=50000
)

print(f"Total grupos retornados por read_group: {len(grupos)}")

# Veamos la estructura RAW de los primeros grupos que tengan account con prefijo 21
print("\nGrupos con prefijo 21/22 en account_id (RAW):")
print("-" * 100)
count_fi = 0
for g in grupos:
    acc_data = g.get('account_id')
    if not acc_data:
        continue
    # acc_data es [id, 'display_name']
    acc_display = acc_data[1] if isinstance(acc_data, (list, tuple)) and len(acc_data) > 1 else str(acc_data)
    
    # Extraer codigo como lo hace el dashboard
    codigo_cuenta = acc_display.split(' ')[0] if ' ' in acc_display else acc_display
    
    if codigo_cuenta[:2] in ['21', '22', '31', '32', '82']:
        concepto = CUENTAS_FIJAS_FINANCIAMIENTO.get(codigo_cuenta, 'NO MAPEADO')
        balance = g.get('balance', 0) or 0
        mes = g.get('date:month', '?')
        count_fi += 1
        print(f"  [{count_fi}] acc_id_raw={acc_data} | code={codigo_cuenta} | concepto={concepto} | balance=${balance:,.0f} | mes={mes}")

print(f"\nTotal grupos con prefijo financiamiento: {count_fi}")

# 4. Veamos TODAS las contrapartidas de un asiento especifico de financiamiento
# Usemos BBci2/2026/0003 que tiene $-1,712,760,000
print(f"\n{'='*80}")
print("DIAGNOSTICO 2: Anatomia de un asiento de financiamiento especifico")
print(f"{'='*80}")

# Buscar el asiento BBci2/2026/0003
asiento_test = search_read(
    'account.move',
    [['name', '=', 'BBci2/2026/0003']],
    ['id', 'name', 'date', 'state', 'move_type', 'journal_id'],
    limit=1
)
if asiento_test:
    print(f"Asiento: {asiento_test[0]}")
    asiento_id = asiento_test[0]['id']
    
    # Todas las lineas del asiento
    lineas = search_read(
        'account.move.line',
        [['move_id', '=', asiento_id]],
        ['id', 'account_id', 'debit', 'credit', 'balance', 'date', 'name'],
        limit=100
    )
    
    print(f"\nLineas del asiento ({len(lineas)}):")
    print(f"{'ID':>8} | {'Account':>40} | {'Debito':>15} | {'Credito':>15} | {'Balance':>15} | {'Es Efectivo':>12}")
    print("-" * 115)
    for l in lineas:
        acc = l.get('account_id', [0, '?'])
        acc_display = acc[1] if isinstance(acc, (list, tuple)) else str(acc)
        acc_id = acc[0] if isinstance(acc, (list, tuple)) else acc
        es_efectivo = "SI EFECTIVO" if acc_id in cuentas_efectivo_ids else ""
        print(f"{l['id']:>8} | {acc_display:>40} | ${l.get('debit', 0):>12,.0f} | ${l.get('credit', 0):>12,.0f} | ${l.get('balance', 0):>12,.0f} | {es_efectivo}")
    
    # Verificar si este asiento_id esta en nuestros asientos_ids
    print(f"\nEste asiento (ID={asiento_id}) esta en asientos_ids? {'SI' if asiento_id in asientos_ids else 'NO'}")
else:
    print("No se encontro el asiento BBci2/2026/0003")

# 5. Busquemos OTRO asiento de financiamiento: ScotC con 21030201
print(f"\n{'='*80}")
print("DIAGNOSTICO 3: Asiento de credito relacionada (21030201)")
print(f"{'='*80}")

asiento_test2 = search_read(
    'account.move',
    [['name', '=', 'ScotC/2026/0000']],
    ['id', 'name', 'date', 'state', 'move_type', 'journal_id'],
    limit=1
)
if asiento_test2:
    print(f"Asiento: {asiento_test2[0]}")
    asiento_id2 = asiento_test2[0]['id']
    
    lineas2 = search_read(
        'account.move.line',
        [['move_id', '=', asiento_id2]],
        ['id', 'account_id', 'debit', 'credit', 'balance', 'date', 'name'],
        limit=100
    )
    
    print(f"\nLineas del asiento ({len(lineas2)}):")
    for l in lineas2:
        acc = l.get('account_id', [0, '?'])
        acc_display = acc[1] if isinstance(acc, (list, tuple)) else str(acc)
        acc_id = acc[0] if isinstance(acc, (list, tuple)) else acc
        es_efectivo = "SI EFECTIVO" if acc_id in cuentas_efectivo_ids else ""
        print(f"  {acc_display:>40} | balance=${l.get('balance', 0):>12,.0f} | {es_efectivo} | {(l.get('name') or '')[:30]}")
    
    print(f"\nEste asiento (ID={asiento_id2}) esta en asientos_ids? {'SI' if asiento_id2 in asientos_ids else 'NO'}")

# 6. TOTALES reales de financiamiento usando search_read directo
print(f"\n{'='*80}")
print("DIAGNOSTICO 4: Totales DIRECTOS de financiamiento (sin read_group)")
print(f"{'='*80}")

fi_codes = list(set(CUENTAS_FIJAS_FINANCIAMIENTO.keys()))
fi_accounts = search_read('account.account', [['code', 'in', fi_codes]], ['id', 'code', 'name'], limit=50)
fi_account_ids = [a['id'] for a in fi_accounts]
fi_code_by_id = {a['id']: a['code'] for a in fi_accounts}

print(f"\nCuentas de financiamiento encontradas en Odoo: {len(fi_accounts)}")
for a in sorted(fi_accounts, key=lambda x: x['code']):
    concepto = CUENTAS_FIJAS_FINANCIAMIENTO.get(a['code'], '?')
    print(f"  {a['code']} ({a['name'][:40]}) -> concepto {concepto}")

# Lineas en asientos que tocaron efectivo, en cuentas de financiamiento
lineas_fi_directo = search_read(
    'account.move.line',
    [['move_id', 'in', asientos_ids], ['account_id', 'in', fi_account_ids], ['parent_state', '=', 'posted']],
    ['id', 'move_id', 'account_id', 'balance', 'date'],
    limit=50000
)

print(f"\nLineas FI en asientos con efectivo: {len(lineas_fi_directo)}")

# Agregar por cuenta y mes
fi_totales = defaultdict(lambda: defaultdict(float))
for l in lineas_fi_directo:
    acc_id = l['account_id'][0] if isinstance(l['account_id'], (list, tuple)) else l['account_id']
    codigo = fi_code_by_id.get(acc_id, '?')
    concepto = CUENTAS_FIJAS_FINANCIAMIENTO.get(codigo, '?')
    mes = str(l['date'])[:7]
    fi_totales[concepto][mes] += l.get('balance', 0) or 0

print("\nTotales por concepto y mes (DIRECTO, sin read_group):")
for concepto in sorted(fi_totales.keys()):
    total_c = sum(fi_totales[concepto].values())
    print(f"\n  {concepto}:")
    for mes in sorted(fi_totales[concepto].keys()):
        print(f"    {mes}: ${fi_totales[concepto][mes]:>15,.0f}")
    print(f"    TOTAL: ${total_c:>15,.0f}")

total_fi = sum(sum(meses.values()) for meses in fi_totales.values())
print(f"\n  GRAN TOTAL FINANCIAMIENTO: ${total_fi:>15,.0f}")

# 7. Comparar con lo que el dashboard probablemente genera
print(f"\n{'='*80}")
print("DIAGNOSTICO 5: Comparacion read_group vs search_read directo")
print(f"{'='*80}")

# Ahora hagamos read_group pero solo con cuentas de financiamiento
grupos_fi_solo = read_group(
    'account.move.line',
    [['move_id', 'in', asientos_ids], ['account_id', 'in', fi_account_ids], ['parent_state', '=', 'posted']],
    ['account_id', 'balance', 'date'],
    ['account_id', 'date:month'],
    limit=50000
)

print(f"\nread_group SOLO financiamiento: {len(grupos_fi_solo)} grupos")
rg_total = 0
for g in grupos_fi_solo:
    acc_data = g.get('account_id')
    acc_display = acc_data[1] if isinstance(acc_data, (list, tuple)) else str(acc_data)
    balance = g.get('balance', 0) or 0
    mes = g.get('date:month', '?')
    rg_total += balance
    print(f"  {acc_display:>40} | mes={mes} | balance=${balance:>12,.0f}")
print(f"  TOTAL read_group: ${rg_total:>12,.0f}")

# 8. Veamos si el problema esta en el filtro account_id NOT IN
print(f"\n{'='*80}")
print("DIAGNOSTICO 6: Verificar superposicion entre efectivo e financiamiento")  
print(f"{'='*80}")

superposicion = set(cuentas_efectivo_ids) & set(fi_account_ids)
if superposicion:
    print(f"\n!!! SUPERPOSICION DETECTADA: {len(superposicion)} cuentas estan TANTO en efectivo como en financiamiento!")
    for acc_id in superposicion:
        info_ef = next((c for c in cuentas_efectivo if c['id'] == acc_id), {})
        info_fi = next((a for a in fi_accounts if a['id'] == acc_id), {})
        print(f"  ID {acc_id}: efectivo={info_ef.get('code', '?')} / financ={info_fi.get('code', '?')}")
    print("\nESTO CAUSA QUE EL FILTRO 'account_id NOT IN cuentas_efectivo_ids' EXCLUYA ESTAS CUENTAS!")
else:
    print("\nNo hay superposicion entre cuentas de efectivo y financiamiento")

print(f"\n{'='*80}")
print("DIAGNOSTICO COMPLETADO")
print(f"{'='*80}")
