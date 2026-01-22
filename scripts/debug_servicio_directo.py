"""
Debug: Llamar directamente al servicio para ver qué retorna
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient
from backend.services.analisis_stock_teorico_service import AnalisisStockTeoricoService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

FECHA_DESDE = "2022-01-01"
FECHA_HASTA = "2026-01-22"

print("=" * 100)
print("DEBUG: LLAMADA DIRECTA AL SERVICIO")
print("=" * 100)

odoo = OdooClient(username=USERNAME, password=PASSWORD)
service = AnalisisStockTeoricoService(odoo)

print("\nLlamando al servicio...")
resultado = service.get_analisis_rango(FECHA_DESDE, FECHA_HASTA)

print("\n" + "=" * 100)
print("RESULTADO DEL SERVICIO:")
print("=" * 100)

resumen = resultado.get('resumen', {})
print(f"\nCompras:  {resumen.get('total_compras_kg', 0):,.0f} kg  ${resumen.get('total_compras_monto', 0):,.0f}")
print(f"Ventas:   {resumen.get('total_ventas_kg', 0):,.0f} kg  ${resumen.get('total_ventas_monto', 0):,.0f}")
print(f"Merma:    {resumen.get('total_merma_kg', 0):,.0f} kg  {resumen.get('pct_merma_historico', 0):.2f}%")

print("\n" + "=" * 100)
print("ESPERADO (de debug_stock_teorico_api.py):")
print("=" * 100)
print(f"\nCompras:  10,527,206 kg")
print(f"Ventas:   8,057,998 kg")
print(f"Merma:    2,469,208 kg  23.46%")

print("\n" + "=" * 100)
