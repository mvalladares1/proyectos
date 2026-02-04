"""
Debug: Verificar qué cuentas del punto 3 FINANCIAMIENTO están siendo procesadas.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.flujo_caja_service import FlujoCajaService
from backend.services.flujo_caja.constants import CUENTAS_FIJAS_FINANCIAMIENTO, ESTRUCTURA_FLUJO

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 100)
print("ANÁLISIS DE CUENTAS DE FINANCIAMIENTO")
print("=" * 100)

# Mostrar mapeo fijo de FINANCIAMIENTO
print("\n1️⃣ MAPEO FIJO DE CUENTAS FINANCIAMIENTO:")
print("-" * 60)
for cuenta, concepto in sorted(CUENTAS_FIJAS_FINANCIAMIENTO.items()):
    print(f"   {cuenta} → {concepto}")

# Mostrar estructura de FINANCIAMIENTO
print(f"\n2️⃣ ESTRUCTURA ESPERADA (IAS 7):")
print("-" * 60)
for linea in ESTRUCTURA_FLUJO.get("FINANCIAMIENTO", {}).get("lineas", []):
    print(f"   {linea['codigo']}: {linea['nombre']} (signo: {linea['signo']})")

# Obtener datos reales
print("\n3️⃣ VERIFICANDO DATOS REALES EN ODOO:")
print("-" * 60)

svc = FlujoCajaService(USERNAME, PASSWORD)

# Buscar movimientos en cuentas de financiamiento
cuentas_fi = list(CUENTAS_FIJAS_FINANCIAMIENTO.keys())
print(f"   Buscando movimientos en cuentas: {cuentas_fi[:5]}... (total: {len(cuentas_fi)})")

try:
    # Buscar cuentas en Odoo
    accs = svc.odoo_manager.odoo.search_read(
        'account.account',
        [['code', 'in', cuentas_fi]],
        ['id', 'code', 'name']
    )
    print(f"\n   Cuentas encontradas en Odoo: {len(accs)}")
    for acc in accs:
        print(f"      - {acc['code']}: {acc['name'][:40]}... (ID: {acc['id']})")
    
    if accs:
        acc_ids = [a['id'] for a in accs]
        
        # Buscar movimientos en los últimos 6 meses
        from datetime import datetime, timedelta
        fecha_fin = datetime.now().strftime('%Y-%m-%d')
        fecha_inicio = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        
        print(f"\n   Buscando movimientos entre {fecha_inicio} y {fecha_fin}...")
        
        movs = svc.odoo_manager.odoo.search_read(
            'account.move.line',
            [
                ['account_id', 'in', acc_ids],
                ['date', '>=', fecha_inicio],
                ['date', '<=', fecha_fin],
                ['parent_state', '=', 'posted']
            ],
            ['id', 'account_id', 'date', 'debit', 'credit', 'balance', 'name'],
            limit=50
        )
        
        print(f"\n   Movimientos encontrados: {len(movs)}")
        if movs:
            total_debit = sum(m['debit'] for m in movs)
            total_credit = sum(m['credit'] for m in movs)
            print(f"   Total Débito: ${total_debit:,.0f}")
            print(f"   Total Crédito: ${total_credit:,.0f}")
            print(f"\n   Últimos 10 movimientos:")
            for m in movs[:10]:
                acc_code = next((a['code'] for a in accs if a['id'] == m['account_id'][0]), '?')
                print(f"      {m['date']}: {acc_code} | D: ${m['debit']:,.0f} | C: ${m['credit']:,.0f} | {m['name'][:30]}")
        else:
            print("   ⚠️ NO HAY MOVIMIENTOS en estas cuentas en los últimos 6 meses!")
            
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Verificar flujo caja para período reciente
print("\n4️⃣ VERIFICANDO FLUJO DE CAJA (último mes):")
print("-" * 60)

try:
    from datetime import datetime, timedelta
    fecha_fin = datetime.now().strftime('%Y-%m-%d')
    fecha_inicio = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-01')
    
    result = svc.get_flujo_mensualizado(fecha_inicio, fecha_fin)
    
    # Verificar actividad FINANCIAMIENTO
    financiamiento = result.get('actividades', {}).get('FINANCIAMIENTO', {})
    print(f"   Subtotal FINANCIAMIENTO: ${financiamiento.get('subtotal', 0):,.0f}")
    
    conceptos = financiamiento.get('conceptos', [])
    print(f"   Conceptos encontrados: {len(conceptos)}")
    
    for concepto in conceptos:
        total = concepto.get('total', 0)
        cuentas = concepto.get('cuentas', [])
        emoji = "✅" if total != 0 else "⚪"
        print(f"   {emoji} {concepto['id']}: {concepto['nombre'][:50]}... = ${total:,.0f}")
        
        if cuentas:
            for cuenta in cuentas[:3]:
                print(f"      └─ {cuenta['codigo']}: ${cuenta['monto']:,.0f}")
                
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 100)
