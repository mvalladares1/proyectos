"""
Script para analizar el impacto de agregar Facturas Proyectadas al flujo de caja
Compara escenarios: SIN presupuestos vs CON presupuestos
"""
import xmlrpc.client
import requests
from datetime import datetime
from collections import defaultdict
import sys

# Fix encoding para Windows
sys.stdout.reconfigure(encoding='utf-8')

# Conexión a Odoo
url = "https://riofuturo.server98c6e.oerpondemand.net"
db = "riofuturo-master"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# API Backend
API_URL = "http://167.114.114.51:8002"

print("=" * 80)
print("📊 ANÁLISIS DE IMPACTO: Facturas Proyectadas en Flujo de Caja")
print("=" * 80)

# ============================================================================
# 1. OBTENER FLUJO DE CAJA ACTUAL (SIN PRESUPUESTOS)
# ============================================================================
print("\n" + "=" * 80)
print("📋 1. FLUJO DE CAJA ACTUAL (Sin Facturas Proyectadas)")
print("=" * 80)

print("\n📡 Consultando API de flujo de caja...")
response = requests.get(
    f"{API_URL}/api/v1/flujo-caja/mensual",
    params={
        "fecha_inicio": "2026-01-01",
        "fecha_fin": "2026-12-31",
        "username": username,
        "password": password
    },
    timeout=60
)

if response.status_code != 200:
    print(f"❌ Error al obtener flujo: {response.status_code}")
    print(response.text)
    exit(1)

flujo_actual = response.json()
print("✅ Flujo actual obtenido")

# Extraer datos de OPERACION actual
operacion_actual = flujo_actual.get("actividades", {}).get("OPERACION", {})
subtotal_actual = operacion_actual.get("subtotal", 0)
subtotales_mes_actual = operacion_actual.get("subtotales_por_mes", {})

print(f"\n📊 OPERACION Subtotal actual: ${subtotal_actual:,.2f}")

# Buscar concepto 1.1.1 CxC
concepto_cxc = None
for concepto in operacion_actual.get("conceptos", []):
    if "Cobros procedentes" in concepto.get("nombre", ""):
        concepto_cxc = concepto
        break

if concepto_cxc:
    print(f"📄 1.1.1 Total actual: ${concepto_cxc.get('total', 0):,.2f}")
    
    # Estados actuales
    print("\n   Estados actuales:")
    for cuenta in concepto_cxc.get("cuentas", []):
        if cuenta.get("es_cuenta_cxc"):
            nombre = cuenta.get("nombre", "")
            monto = cuenta.get("monto", 0)
            print(f"      {nombre}: ${monto:,.2f}")

# ============================================================================
# 2. OBTENER PRESUPUESTOS DE VENTAS
# ============================================================================
print("\n" + "=" * 80)
print("📋 2. PRESUPUESTOS DE VENTAS (Facturas Proyectadas)")
print("=" * 80)

# Conectar a Odoo
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Buscar presupuestos
presupuestos = models.execute_kw(db, uid, password, 'sale.order', 'search_read',
    [[
        ['state', 'in', ['draft', 'sent']],
        ['date_order', '>=', '2026-01-01'],
        ['date_order', '<=', '2026-12-31']
    ]],
    {
        'fields': [
            'name', 'partner_id', 'commitment_date', 'date_order',
            'amount_total', 'currency_id'
        ]
    })

print(f"\n📊 Total presupuestos: {len(presupuestos)}")

# Agrupar por mes
presupuestos_por_mes = defaultdict(float)
presupuestos_por_cliente = defaultdict(float)

for pres in presupuestos:
    fecha_ref = pres.get('commitment_date') or pres.get('date_order')
    
    if fecha_ref and isinstance(fecha_ref, str):
        try:
            fecha_dt = datetime.strptime(fecha_ref.split(' ')[0], '%Y-%m-%d')
            mes_key = fecha_dt.strftime('%Y-%m')
            
            monto = pres.get('amount_total', 0)
            cliente = pres.get('partner_id', [False, 'Sin cliente'])[1] if pres.get('partner_id') else 'Sin cliente'
            
            presupuestos_por_mes[mes_key] += monto
            presupuestos_por_cliente[cliente] += monto
        except:
            pass

total_presupuestos = sum(presupuestos_por_mes.values())
print(f"💰 Total presupuestado: ${total_presupuestos:,.2f}")

print("\n📅 Por mes:")
for mes in sorted(presupuestos_por_mes.keys()):
    print(f"   {mes}: ${presupuestos_por_mes[mes]:,.2f}")

# ============================================================================
# 3. CALCULAR FLUJO PROYECTADO (CON PRESUPUESTOS)
# ============================================================================
print("\n" + "=" * 80)
print("📊 3. FLUJO PROYECTADO (Con Facturas Proyectadas)")
print("=" * 80)

# Nuevo subtotal de CxC (agregar presupuestos)
cxc_actual = concepto_cxc.get('total', 0) if concepto_cxc else 0
cxc_proyectado = cxc_actual + total_presupuestos

print(f"\n📄 1.1.1 Cobros de ventas:")
print(f"   Actual: ${cxc_actual:,.2f}")
print(f"   + Facturas Proyectadas: ${total_presupuestos:,.2f}")
print(f"   = Proyectado: ${cxc_proyectado:,.2f}")
print(f"   Incremento: ${total_presupuestos:,.2f} ({(total_presupuestos/cxc_actual*100) if cxc_actual else 0:.1f}%)")

# Nuevo subtotal de OPERACION
operacion_proyectado = subtotal_actual + total_presupuestos

print(f"\n📊 OPERACION Subtotal:")
print(f"   Actual: ${subtotal_actual:,.2f}")
print(f"   + Facturas Proyectadas: ${total_presupuestos:,.2f}")
print(f"   = Proyectado: ${operacion_proyectado:,.2f}")
print(f"   Incremento: ${total_presupuestos:,.2f}")

# ============================================================================
# 4. COMPARACIÓN MES A MES
# ============================================================================
print("\n" + "=" * 80)
print("📅 4. COMPARACIÓN MES A MES")
print("=" * 80)

meses_todos = sorted(set(list(subtotales_mes_actual.keys()) + list(presupuestos_por_mes.keys())))

print("\n{:<12} {:>18} {:>18} {:>18}".format("MES", "ACTUAL", "PROYECTADOS", "TOTAL PROYECTADO"))
print("-" * 80)

for mes in meses_todos:
    actual_mes = subtotales_mes_actual.get(mes, 0)
    proyectado_mes = presupuestos_por_mes.get(mes, 0)
    total_mes = actual_mes + proyectado_mes
    
    print("{:<12} ${:>16,.0f} ${:>16,.0f} ${:>16,.0f}".format(
        mes, actual_mes, proyectado_mes, total_mes
    ))

# ============================================================================
# 5. TOP CLIENTES EN PRESUPUESTOS
# ============================================================================
print("\n" + "=" * 80)
print("👥 5. TOP 10 CLIENTES EN FACTURAS PROYECTADAS")
print("=" * 80)

print("\n{:<50} {:>18}".format("CLIENTE", "MONTO PROYECTADO"))
print("-" * 80)

for i, (cliente, monto) in enumerate(sorted(presupuestos_por_cliente.items(), 
                                             key=lambda x: x[1], 
                                             reverse=True)[:10], 1):
    print("{:2}. {:<47} ${:>16,.0f}".format(i, cliente[:47], monto))

# ============================================================================
# 6. RECOMENDACIONES
# ============================================================================
print("\n" + "=" * 80)
print("💡 6. RECOMENDACIONES")
print("=" * 80)

pct_incremento = (total_presupuestos / abs(subtotal_actual) * 100) if subtotal_actual != 0 else 0

print(f"\n📊 Impacto de agregar Facturas Proyectadas:")
print(f"   • Incremento en OPERACION: {pct_incremento:.1f}%")
print(f"   • Monto adicional: ${total_presupuestos:,.2f}")
print(f"   • {len(presupuestos)} presupuestos")
print(f"   • {len(presupuestos_por_cliente)} clientes")

print("\n✅ Implementación recomendada:")
print("   1. Agregar toggle 'Incluir Facturas Proyectadas' (checkbox)")
print("   2. Mostrar como nuevo estado en 1.1.1:")
print("      🔮 Facturas Proyectadas (presupuestos)")
print("   3. Usar ícono distintivo para diferenciar de facturas reales")
print("   4. Permitir expandir para ver clientes individuales")
print("   5. El toggle 'Solo pendiente' NO debe afectar las proyectadas")

print("\n⚠️  Consideraciones:")
print("   • Estas son proyecciones, no compromisos confirmados")
print("   • Presupuestos pueden cancelarse o modificarse")
print("   • Usar para planificación, no para contabilidad formal")
print("   • Monitorear tasa de conversión presupuesto → venta real")

print("\n" + "=" * 80)
print("✅ ANÁLISIS DE IMPACTO COMPLETO")
print("=" * 80)
