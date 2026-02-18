"""
Script para explorar presupuestos de ventas en Odoo
y determinar cómo integrarlos como "Facturas Proyectadas" en el flujo de caja
"""
import xmlrpc.client
from datetime import datetime
from collections import defaultdict

# Conexión a Odoo
url = "https://riofuturo.server98c6e.oerpondemand.net"
db = "riofuturo-master"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 80)
print("🔍 EXPLORACIÓN: Presupuestos de Ventas para Facturas Proyectadas")
print("=" * 80)

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"\n✅ Conectado como: {username}")
print(f"   UID: {uid}")

# ============================================================================
# 1. BUSCAR PRESUPUESTOS (sale.order en estados draft, sent)
# ============================================================================
print("\n" + "=" * 80)
print("📋 1. PRESUPUESTOS ACTIVOS (Draft/Sent)")
print("=" * 80)

presupuestos = models.execute_kw(db, uid, password, 'sale.order', 'search_read',
    [[
        ['state', 'in', ['draft', 'sent']],
        ['date_order', '>=', '2026-01-01'],
        ['date_order', '<=', '2026-12-31']
    ]],
    {
        'fields': [
            'name', 'partner_id', 'date_order', 'validity_date', 
            'amount_total', 'currency_id', 'state', 'user_id',
            'commitment_date', 'expected_date'
        ],
        'limit': 20,
        'order': 'date_order desc'
    })

print(f"\n📊 Total presupuestos encontrados: {len(presupuestos)}")

if presupuestos:
    print("\n📝 Primeros 10 presupuestos:")
    print("-" * 80)
    
    for pres in presupuestos[:10]:
        nombre = pres.get('name', 'Sin nombre')
        cliente = pres.get('partner_id', [False, 'Sin cliente'])[1] if pres.get('partner_id') else 'Sin cliente'
        monto = pres.get('amount_total', 0)
        moneda = pres.get('currency_id', [False, 'CLP'])[1] if pres.get('currency_id') else 'CLP'
        estado = pres.get('state', 'draft')
        fecha_orden = pres.get('date_order', 'Sin fecha')
        fecha_validez = pres.get('validity_date', 'Sin fecha validez')
        fecha_compromiso = pres.get('commitment_date', 'Sin compromiso')
        fecha_esperada = pres.get('expected_date', 'Sin esperada')
        
        print(f"\n  📄 {nombre}")
        print(f"     Cliente: {cliente}")
        print(f"     Monto: ${monto:,.2f} {moneda}")
        print(f"     Estado: {estado.upper()}")
        print(f"     Fecha orden: {fecha_orden}")
        print(f"     Validez hasta: {fecha_validez}")
        print(f"     Fecha compromiso: {fecha_compromiso}")
        print(f"     Fecha esperada: {fecha_esperada}")

# ============================================================================
# 2. ANALIZAR ESTRUCTURA DE FECHAS
# ============================================================================
print("\n" + "=" * 80)
print("📅 2. ANÁLISIS DE FECHAS")
print("=" * 80)

con_commitment = 0
con_expected = 0
con_validity = 0
sin_fecha_ref = 0

for pres in presupuestos:
    if pres.get('commitment_date'):
        con_commitment += 1
    if pres.get('expected_date'):
        con_expected += 1
    if pres.get('validity_date'):
        con_validity += 1
    
    if not pres.get('commitment_date') and not pres.get('expected_date'):
        sin_fecha_ref += 1

print(f"\n📊 Estadísticas de fechas:")
print(f"   Con commitment_date: {con_commitment} ({con_commitment/len(presupuestos)*100:.1f}%)")
print(f"   Con expected_date: {con_expected} ({con_expected/len(presupuestos)*100:.1f}%)")
print(f"   Con validity_date: {con_validity} ({con_validity/len(presupuestos)*100:.1f}%)")
print(f"   Sin fecha de referencia: {sin_fecha_ref} ({sin_fecha_ref/len(presupuestos)*100:.1f}%)")

print("\n💡 Fecha recomendada para proyección:")
if con_commitment > len(presupuestos) * 0.5:
    print("   → commitment_date (fecha compromiso con cliente)")
elif con_expected > len(presupuestos) * 0.5:
    print("   → expected_date (fecha esperada)")
else:
    print("   → validity_date (validez del presupuesto) o date_order + 30 días")

# ============================================================================
# 3. AGRUPAR POR MES (para integrar al flujo de caja)
# ============================================================================
print("\n" + "=" * 80)
print("📊 3. AGRUPACIÓN POR MES")
print("=" * 80)

montos_por_mes = defaultdict(float)
presupuestos_por_mes = defaultdict(list)

for pres in presupuestos:
    # Determinar fecha a usar (prioridad: commitment_date > expected_date > validity_date > date_order)
    fecha_ref = pres.get('commitment_date') or pres.get('expected_date') or pres.get('validity_date') or pres.get('date_order')
    
    if fecha_ref and isinstance(fecha_ref, str):
        try:
            fecha_dt = datetime.strptime(fecha_ref.split(' ')[0], '%Y-%m-%d')
            mes_key = fecha_dt.strftime('%Y-%m')
            
            monto = pres.get('amount_total', 0)
            montos_por_mes[mes_key] += monto
            presupuestos_por_mes[mes_key].append({
                'nombre': pres.get('name'),
                'cliente': pres.get('partner_id', [False, 'Sin cliente'])[1] if pres.get('partner_id') else 'Sin cliente',
                'monto': monto
            })
        except:
            pass

print("\n📅 Presupuestos proyectados por mes:")
print("-" * 80)

for mes in sorted(montos_por_mes.keys()):
    total = montos_por_mes[mes]
    cant = len(presupuestos_por_mes[mes])
    print(f"\n  📆 {mes}: ${total:,.2f} ({cant} presupuestos)")
    
    # Mostrar top 3 por mes
    top_3 = sorted(presupuestos_por_mes[mes], key=lambda x: x['monto'], reverse=True)[:3]
    for i, p in enumerate(top_3, 1):
        print(f"     {i}. {p['cliente']}: ${p['monto']:,.2f} ({p['nombre']})")

# ============================================================================
# 4. BUSCAR ÓRDENES DE VENTA CONFIRMADAS (para comparación)
# ============================================================================
print("\n" + "=" * 80)
print("📦 4. ÓRDENES DE VENTA CONFIRMADAS (para comparación)")
print("=" * 80)

ordenes_confirmadas = models.execute_kw(db, uid, password, 'sale.order', 'search_read',
    [[
        ['state', 'in', ['sale']],
        ['date_order', '>=', '2026-01-01'],
        ['date_order', '<=', '2026-12-31']
    ]],
    {
        'fields': ['name', 'partner_id', 'amount_total', 'state'],
        'limit': 10
    })

print(f"\n📊 Órdenes confirmadas encontradas: {len(ordenes_confirmadas)}")
if ordenes_confirmadas:
    total_confirmado = sum(o.get('amount_total', 0) for o in ordenes_confirmadas)
    print(f"   Total confirmado: ${total_confirmado:,.2f}")

# ============================================================================
# 5. RESUMEN Y RECOMENDACIONES
# ============================================================================
print("\n" + "=" * 80)
print("📌 5. RESUMEN Y RECOMENDACIONES")
print("=" * 80)

total_presupuestado = sum(montos_por_mes.values())
print(f"\n💰 Total presupuestado (2026): ${total_presupuestado:,.2f}")
print(f"📋 Total presupuestos: {len(presupuestos)}")

print("\n✅ Recomendaciones para implementación:")
print("   1. Agregar toggle 'Incluir Facturas Proyectadas' en la UI")
print("   2. Crear estado 'estado_draft' o 'estado_proyectado' en CxC")
print("   3. Usar commitment_date como fecha de proyección (si existe)")
print("   4. Agrupar por cliente igual que las facturas reales")
print("   5. Mostrar con ícono distintivo (ej: 🔮 Facturas Proyectadas)")
print("   6. Permitir filtrar/excluir en el toggle 'Solo pendiente'")

print("\n🎨 Estructura sugerida en el dashboard:")
print("   1.1.1 - Cobros procedentes de las ventas...")
print("      └─ 🔮 Facturas Proyectadas (presupuestos)  [NUEVO]")
print("      └─ ✅ Facturas Pagadas")
print("      └─ ⏳ Facturas Parcialmente Pagadas")
print("      └─ ❌ Facturas No Pagadas")
print("      └─ ↩️ Facturas Revertidas")

print("\n" + "=" * 80)
