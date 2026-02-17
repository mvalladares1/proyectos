"""
Script detallado de presupuestos de ventas
Muestra líneas de productos, montos totales, y estructura completa
"""
import xmlrpc.client
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

print("=" * 80)
print("🔍 ANÁLISIS DETALLADO: Presupuestos de Ventas")
print("=" * 80)

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"\n✅ Conectado")

# ============================================================================
# 1. BUSCAR PRESUPUESTOS CON MÁS DETALLE
# ============================================================================
print("\n" + "=" * 80)
print("📋 1. PRESUPUESTOS DETALLADOS (2026)")
print("=" * 80)

# Buscar presupuestos
presupuestos = models.execute_kw(db, uid, password, 'sale.order', 'search_read',
    [[
        ['state', 'in', ['draft', 'sent']],
        ['date_order', '>=', '2026-01-01'],
        ['date_order', '<=', '2026-12-31']
    ]],
    {
        'fields': [
            'id', 'name', 'partner_id', 'date_order', 'commitment_date',
            'amount_untaxed', 'amount_tax', 'amount_total', 'currency_id',
            'state', 'user_id', 'order_line', 'note', 'client_order_ref'
        ],
        'order': 'commitment_date asc'
    })

print(f"\n📊 Total presupuestos: {len(presupuestos)}")

# Agrupar por cliente
presupuestos_por_cliente = defaultdict(list)
for pres in presupuestos:
    cliente_id = pres.get('partner_id', [False])[0] if pres.get('partner_id') else None
    cliente_nombre = pres.get('partner_id', [False, 'Sin cliente'])[1] if pres.get('partner_id') else 'Sin cliente'
    presupuestos_por_cliente[cliente_nombre].append(pres)

print(f"📊 Clientes únicos: {len(presupuestos_por_cliente)}")

# ============================================================================
# 2. MOSTRAR DETALLE POR CLIENTE
# ============================================================================
print("\n" + "=" * 80)
print("👥 2. DETALLE POR CLIENTE")
print("=" * 80)

for cliente, pres_list in sorted(presupuestos_por_cliente.items(), 
                                   key=lambda x: sum(p.get('amount_total', 0) for p in x[1]), 
                                   reverse=True):
    total_cliente = sum(p.get('amount_total', 0) for p in pres_list)
    print(f"\n🏢 {cliente}")
    print(f"   Total: ${total_cliente:,.2f} ({len(pres_list)} presupuestos)")
    print("-" * 80)
    
    for pres in sorted(pres_list, key=lambda x: x.get('commitment_date') or '9999-12-31'):
        nombre = pres.get('name', 'Sin nombre')
        monto = pres.get('amount_total', 0)
        monto_sin_imp = pres.get('amount_untaxed', 0)
        impuestos = pres.get('amount_tax', 0)
        fecha_comp = pres.get('commitment_date', 'Sin fecha')
        moneda = pres.get('currency_id', [False, 'CLP'])[1] if pres.get('currency_id') else 'CLP'
        estado = pres.get('state', 'draft').upper()
        
        # Convertir fecha
        try:
            fecha_dt = datetime.strptime(fecha_comp.split(' ')[0], '%Y-%m-%d')
            fecha_comp_fmt = fecha_dt.strftime('%Y-%m-%d')
        except:
            fecha_comp_fmt = fecha_comp
        
        print(f"  📄 {nombre} - {fecha_comp_fmt}")
        print(f"     Estado: {estado}")
        print(f"     Subtotal: ${monto_sin_imp:,.2f} {moneda}")
        print(f"     Impuestos: ${impuestos:,.2f}")
        print(f"     Total: ${monto:,.2f} {moneda}")
        
        # Obtener líneas del presupuesto
        if pres.get('order_line'):
            line_ids = pres.get('order_line', [])[:5]  # Primeras 5 líneas
            try:
                lineas = models.execute_kw(db, uid, password, 'sale.order.line', 'read',
                    [line_ids],
                    {'fields': ['product_id', 'name', 'product_uom_qty', 'price_unit', 'price_subtotal']})
                
                if lineas:
                    print(f"     Productos:")
                    for linea in lineas[:3]:  # Primeras 3 líneas
                        prod_nombre = linea.get('product_id', [False, 'Producto'])[1] if linea.get('product_id') else 'Producto'
                        qty = linea.get('product_uom_qty', 0)
                        precio = linea.get('price_unit', 0)
                        subtotal = linea.get('price_subtotal', 0)
                        print(f"       • {prod_nombre}: {qty:.2f} x ${precio:,.2f} = ${subtotal:,.2f}")
            except:
                pass
        
        print()

# ============================================================================
# 3. AGRUPACIÓN POR MES
# ============================================================================
print("\n" + "=" * 80)
print("📅 3. PROYECCIÓN POR MES")
print("=" * 80)

montos_por_mes = defaultdict(lambda: {'total': 0, 'presupuestos': [], 'por_cliente': defaultdict(float)})

for pres in presupuestos:
    fecha_comp = pres.get('commitment_date') or pres.get('date_order')
    
    if fecha_comp and isinstance(fecha_comp, str):
        try:
            fecha_dt = datetime.strptime(fecha_comp.split(' ')[0], '%Y-%m-%d')
            mes_key = fecha_dt.strftime('%Y-%m')
            
            monto = pres.get('amount_total', 0)
            cliente = pres.get('partner_id', [False, 'Sin cliente'])[1] if pres.get('partner_id') else 'Sin cliente'
            
            montos_por_mes[mes_key]['total'] += monto
            montos_por_mes[mes_key]['presupuestos'].append(pres.get('name'))
            montos_por_mes[mes_key]['por_cliente'][cliente] += monto
        except:
            pass

print("\n📊 Proyección mensual:")
for mes in sorted(montos_por_mes.keys()):
    data = montos_por_mes[mes]
    total = data['total']
    cant = len(data['presupuestos'])
    
    print(f"\n  📆 {mes}: ${total:,.2f} ({cant} presupuestos)")
    
    # Top 3 clientes por mes
    top_clientes = sorted(data['por_cliente'].items(), key=lambda x: x[1], reverse=True)[:3]
    for i, (cliente, monto_cli) in enumerate(top_clientes, 1):
        print(f"       {i}. {cliente}: ${monto_cli:,.2f}")

# ============================================================================
# 4. ANÁLISIS DE DISTRIBUCIÓN
# ============================================================================
print("\n" + "=" * 80)
print("📊 4. ANÁLISIS DE DISTRIBUCIÓN")
print("=" * 80)

total_general = sum(p.get('amount_total', 0) for p in presupuestos)
print(f"\n💰 Total general: ${total_general:,.2f}")

# Por estado
por_estado = defaultdict(lambda: {'count': 0, 'total': 0})
for pres in presupuestos:
    estado = pres.get('state', 'unknown')
    por_estado[estado]['count'] += 1
    por_estado[estado]['total'] += pres.get('amount_total', 0)

print(f"\n📋 Por estado:")
for estado, data in sorted(por_estado.items()):
    pct = (data['total'] / total_general * 100) if total_general > 0 else 0
    print(f"   {estado.upper()}: ${data['total']:,.2f} ({data['count']} presupuestos, {pct:.1f}%)")

# Por moneda
por_moneda = defaultdict(lambda: {'count': 0, 'total': 0})
for pres in presupuestos:
    moneda = pres.get('currency_id', [False, 'CLP'])[1] if pres.get('currency_id') else 'CLP'
    por_moneda[moneda]['count'] += 1
    por_moneda[moneda]['total'] += pres.get('amount_total', 0)

print(f"\n💱 Por moneda:")
for moneda, data in sorted(por_moneda.items(), key=lambda x: x[1]['total'], reverse=True):
    print(f"   {moneda}: ${data['total']:,.2f} ({data['count']} presupuestos)")

# ============================================================================
# 5. FILTROS RECOMENDADOS
# ============================================================================
print("\n" + "=" * 80)
print("🎯 5. FILTROS RECOMENDADOS")
print("=" * 80)

print("\n✅ Criterios sugeridos para incluir en flujo de caja:")
print("   1. Estado: ['draft', 'sent'] ✓ (presupuestos activos)")
print("   2. Fecha: commitment_date (disponible en 100%)")
print("   3. Moneda: Considerar todas (convertir a CLP si es necesario)")
print("   4. Clientes: Todos (sin exclusiones por ahora)")

print("\n❌ Presupuestos que NO deberíamos incluir:")
print("   • Estado 'cancel' (cancelados)")
print("   • Estado 'sale' (ya confirmados - estos generan facturas reales)")
print("   • Presupuestos muy antiguos sin commitment_date")

print("\n💡 Opciones de configuración sugeridas:")
print("   • Toggle: 'Incluir Facturas Proyectadas' (checkbox en UI)")
print("   • Filtro por moneda (opcional)")
print("   • Filtro por cliente (opcional)")
print("   • Umbral mínimo de monto (opcional)")

print("\n" + "=" * 80)
print("✅ ANÁLISIS COMPLETO")
print("=" * 80)
