"""
Debug: Verificar lógica de calcular_cobros_clientes DIRECTAMENTE
Este script NO usa Docker - ejecuta la lógica directamente con Python
"""
import os
import sys
from collections import defaultdict
from datetime import datetime

# Agregar paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Simular la función _fecha_a_periodo para verificar
def fecha_a_periodo(fecha: str, periodos_lista: list) -> str:
    """Convierte fecha a período semanal."""
    if not fecha:
        return ''
    
    if not periodos_lista or len(periodos_lista) == 0:
        return fecha[:7]
    
    primer_periodo = str(periodos_lista[0])
    es_semanal = 'W' in primer_periodo or '-W' in primer_periodo
    
    if es_semanal:
        try:
            fecha_dt = datetime.strptime(fecha[:10], '%Y-%m-%d')
            isocalendar = fecha_dt.isocalendar()
            year = isocalendar[0]
            week = isocalendar[1]
            return f"{year}-W{week:02d}"
        except Exception as e:
            print(f"Error: {e}")
            return fecha[:7]
    else:
        return fecha[:7]


print("=" * 80)
print("SIMULACIÓN DE LÓGICA 1.1.1")
print("=" * 80)

# Datos de prueba - Factura TRONADOR FCXE 281
factura = {
    'name': 'FCXE 000281',
    'invoice_date': '2026-01-12',
    'invoice_date_due': '2026-01-12',
    'x_studio_fecha_estimada_de_pago': '2026-01-19',
    'amount_total': 140400,  # USD
    'amount_residual': 6077,  # USD
    'payment_state': 'partial',
    'currency_id': [2, 'USD']
}

# Lista de semanas (como las genera el API)
meses_lista = ['2026-W01', '2026-W02', '2026-W03', '2026-W04', '2026-W05']

print(f"\nFACTURA DE PRUEBA:")
print(f"  Número: {factura['name']}")
print(f"  invoice_date: {factura['invoice_date']}")
print(f"  x_studio_fecha_estimada_de_pago: {factura['x_studio_fecha_estimada_de_pago']}")
print(f"  amount_total: ${factura['amount_total']:,.2f} USD")
print(f"  amount_residual: ${factura['amount_residual']:,.2f} USD")
print(f"  payment_state: {factura['payment_state']}")

print(f"\nCALCULANDO PERÍODOS:")

# Calcular periodo_real (basado en invoice_date)
periodo_real = fecha_a_periodo(factura['invoice_date'], meses_lista)
print(f"  periodo_real (invoice_date {factura['invoice_date']}): {periodo_real}")

# Calcular periodo_proyectado (basado en fecha_estimada o invoice_date_due)
fecha_estimada = factura.get('x_studio_fecha_estimada_de_pago')
fecha_vencimiento = factura.get('invoice_date_due')

if fecha_estimada:
    periodo_proyectado = fecha_a_periodo(str(fecha_estimada)[:10], meses_lista)
    print(f"  periodo_proyectado (x_studio_fecha_estimada {fecha_estimada}): {periodo_proyectado}")
elif fecha_vencimiento:
    periodo_proyectado = fecha_a_periodo(str(fecha_vencimiento)[:10], meses_lista)
    print(f"  periodo_proyectado (invoice_date_due {fecha_vencimiento}): {periodo_proyectado}")
else:
    periodo_proyectado = periodo_real
    print(f"  periodo_proyectado (fallback a real): {periodo_proyectado}")

# Calcular montos
amount_total = factura['amount_total']
amount_residual = factura['amount_residual']

# Simular conversión USD a CLP (tasa ~900)
TASA_USD_CLP = 900
currency_name = factura['currency_id'][1] if factura['currency_id'] else ''
if 'USD' in str(currency_name).upper():
    amount_total_clp = amount_total * TASA_USD_CLP
    amount_residual_clp = amount_residual * TASA_USD_CLP
    print(f"\nCONVERSIÓN USD→CLP (tasa {TASA_USD_CLP}):")
    print(f"  amount_total: ${amount_total:,.2f} USD → ${amount_total_clp:,.0f} CLP")
    print(f"  amount_residual: ${amount_residual:,.2f} USD → ${amount_residual_clp:,.0f} CLP")
else:
    amount_total_clp = amount_total
    amount_residual_clp = amount_residual

cobrado = amount_total_clp - amount_residual_clp
pendiente = amount_residual_clp

print(f"\nDISTRIBUCIÓN DE MONTOS:")
print(f"  Cobrado (real): ${cobrado:,.0f} CLP → va a {periodo_real}")
print(f"  Pendiente (proyectado): ${pendiente:,.0f} CLP → va a {periodo_proyectado}")

print(f"\nRESULTADO ESPERADO EN montos_por_mes:")
montos_por_mes = defaultdict(float)
montos_por_mes[periodo_real] += cobrado
montos_por_mes[periodo_proyectado] += pendiente

for periodo, monto in sorted(montos_por_mes.items()):
    # Convertir W03 a S3 para comparar con UI
    num_semana = int(periodo.split('-W')[1])
    print(f"  {periodo} (S{num_semana}): ${monto:,.0f} CLP")

print("\n" + "=" * 80)
print("COMPARACIÓN CON DASHBOARD:")
print("=" * 80)
print(f"Dashboard muestra TRONADOR en S4 con $125,923,356")
print(f"Esperado según lógica nueva:")
print(f"  S3 (W03): ${cobrado:,.0f} (cobrado)")
print(f"  S4 (W04): ${pendiente:,.0f} (pendiente)")
print("\n⚠️ Si el dashboard sigue mostrando $125M en S4 solamente,")
print("   significa que el código nuevo NO se está ejecutando.")
