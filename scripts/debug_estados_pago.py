"""
Debug: Analizar facturas por ESTADO DE PAGO para diseñar nueva estructura.

Nueva estructura propuesta:
- Nivel 2: Cuenta (11030101 - Deudores)
- Nivel 3: Estado de pago
  - Pagadas
  - Parcialmente Pagadas
  - En Proceso de Pago
  - No Pagadas
- Nivel 4: Facturas individuales

Casos especiales:
- Factura con fecha_pago DIC 2025, parcialmente pagada
  -> Mostrar monto parcial en DIC 2025
  -> Mostrar saldo pendiente en mes actual (FEB 2026) como atrasado
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient
from datetime import datetime

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

odoo = OdooClient(
    url="https://riofuturo.server98c6e.oerpondemand.net",
    db="riofuturo-master",
    username=USERNAME,
    password=PASSWORD
)

print("=" * 100)
print("ANÁLISIS DE FACTURAS POR ESTADO DE PAGO - OCT/NOV/DIC 2025")
print("=" * 100)

# Buscar facturas de cliente con fecha de pago en OCT-DIC 2025
facturas = odoo.search_read(
    'account.move',
    [
        ('move_type', '=', 'out_invoice'),
        ('state', '=', 'posted'),
        ('x_studio_fecha_de_pago', '>=', '2025-10-01'),
        ('x_studio_fecha_de_pago', '<=', '2025-12-31')
    ],
    [
        'name', 'invoice_date', 'x_studio_fecha_de_pago', 'payment_state',
        'amount_total', 'amount_residual', 'partner_id'
    ],
    limit=200
)

print(f"\nFacturas encontradas: {len(facturas)}\n")

# Agrupar por estado de pago
por_estado = {
    'not_paid': [],
    'partial': [],
    'in_payment': [],
    'paid': [],
    'reversed': []
}

for fac in facturas:
    estado = fac.get('payment_state', 'not_paid')
    if estado not in por_estado:
        por_estado[estado] = []
    por_estado[estado].append(fac)

# Mostrar estadísticas
print("RESUMEN POR ESTADO DE PAGO:")
print("-" * 100)
for estado, lista in por_estado.items():
    if lista:
        total_monto = sum(f.get('amount_total', 0) for f in lista)
        total_residual = sum(f.get('amount_residual', 0) for f in lista)
        print(f"{estado:15s}: {len(lista):3d} facturas | Total: ${total_monto:>15,.0f} | Saldo: ${total_residual:>15,.0f}")

# Analizar facturas PARCIALMENTE PAGADAS (caso especial)
print("\n" + "=" * 100)
print("DETALLE: FACTURAS PARCIALMENTE PAGADAS (Caso especial para proyección)")
print("=" * 100)

for fac in por_estado.get('partial', []):
    nombre = fac['name']
    fecha_pago = fac.get('x_studio_fecha_de_pago')
    total = fac.get('amount_total', 0)
    residual = fac.get('amount_residual', 0)
    pagado = total - residual
    
    # Determinar mes de fecha_pago
    mes_pago = fecha_pago[:7] if fecha_pago else 'Sin fecha'
    
    print(f"\n{nombre}:")
    print(f"  Fecha de pago: {fecha_pago} (Mes: {mes_pago})")
    print(f"  Total:         ${total:>15,.0f}")
    print(f"  Pagado:        ${pagado:>15,.0f}")
    print(f"  Saldo:         ${residual:>15,.0f}")
    print(f"  → Proyección propuesta:")
    print(f"     - Mostrar ${pagado:,.0f} en {mes_pago} (monto pagado)")
    print(f"     - Mostrar ${residual:,.0f} en 2026-02 (saldo atrasado)")

# Analizar facturas NO PAGADAS con fecha pasada
print("\n" + "=" * 100)
print("DETALLE: FACTURAS NO PAGADAS CON FECHA VENCIDA (Deuda atrasada)")
print("=" * 100)

hoy = datetime.now().date()
facturas_atrasadas = []

for fac in por_estado.get('not_paid', []):
    fecha_pago = fac.get('x_studio_fecha_de_pago')
    if fecha_pago:
        from datetime import date
        fecha_obj = date.fromisoformat(fecha_pago)
        if fecha_obj < hoy:
            facturas_atrasadas.append(fac)

print(f"\nFacturas no pagadas con fecha vencida: {len(facturas_atrasadas)}")
for fac in facturas_atrasadas[:10]:  # Mostrar primeras 10
    nombre = fac['name']
    fecha_pago = fac.get('x_studio_fecha_de_pago')
    total = fac.get('amount_total', 0)
    dias_atraso = (hoy - date.fromisoformat(fecha_pago)).days
    
    print(f"\n{nombre}:")
    print(f"  Fecha de pago: {fecha_pago} ({dias_atraso} días de atraso)")
    print(f"  Monto:         ${total:>15,.0f}")
    print(f"  → Proyección propuesta:")
    print(f"     - Mostrar ${total:,.0f} en 2026-02 (mes actual - deuda atrasada)")

# Resumen de la nueva estructura
print("\n" + "=" * 100)
print("RESUMEN: NUEVA ESTRUCTURA DE VISUALIZACIÓN PROPUESTA")
print("=" * 100)
print("""
Nivel 1: 1.1.1 - Cobros procedentes de ventas
    |
    └─ Nivel 2: 11030101 - DEUDORES POR VENTAS
        |
        ├─ Nivel 3: Facturas Pagadas
        |   └─ Nivel 4: FAC 000225, FAC 000222, etc.
        |
        ├─ Nivel 3: Facturas Parcialmente Pagadas
        |   ├─ Distribución por mes:
        |   |   - Mes fecha_pago: Monto pagado
        |   |   - Mes actual: Saldo pendiente (atrasado)
        |   └─ Nivel 4: FAC XXX (parcial), etc.
        |
        ├─ Nivel 3: Facturas en Proceso de Pago
        |   └─ Nivel 4: FAC YYY, etc.
        |
        └─ Nivel 3: Facturas No Pagadas
            ├─ Distribución:
            |   - Si fecha_pago < hoy: Mostrar en mes actual (atrasado)
            |   - Si fecha_pago >= hoy: Mostrar en mes de fecha_pago (proyección)
            └─ Nivel 4: FAC ZZZ, etc.
""")

print("\n✅ Análisis completado")
