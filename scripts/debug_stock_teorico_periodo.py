"""
DEBUG: Stock Teórico Anual - Resultados por Período
Ejecuta el servicio mejorado y muestra resultados detallados
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient
from backend.services.analisis_stock_teorico_service import AnalisisStockTeoricoService

# Configuración
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Período a analizar (temporadas)
ANIOS = [2024, 2025]  # Temporada 2024 = nov 2023 a oct 2024
FECHA_CORTE = "10-31"  # 31 de octubre

print("=" * 140)
print("DEBUG: STOCK TEÓRICO ANUAL - ANÁLISIS DE PERÍODO")
print("=" * 140)
print(f"Temporadas a analizar: {ANIOS}")
print(f"Fecha de corte: {FECHA_CORTE}")
print("=" * 140)

odoo = OdooClient(username=USERNAME, password=PASSWORD)
servicio = AnalisisStockTeoricoService(odoo)

print("\n🔄 Ejecutando análisis multi-anual...")
resultado = servicio.get_analisis_multi_anual(ANIOS, FECHA_CORTE)

print("\n" + "=" * 140)
print("RESUMEN GENERAL CONSOLIDADO")
print("=" * 140)

resumen = resultado.get('resumen_general', {})
print(f"\n📊 TOTALES CONSOLIDADOS:")
print(f"   Compras:  {resumen.get('total_compras_kg', 0):,.2f} kg  |  ${resumen.get('total_compras_valor', 0):,.2f}")
print(f"   Ventas:   {resumen.get('total_ventas_kg', 0):,.2f} kg  |  ${resumen.get('total_ventas_valor', 0):,.2f}")
print(f"   Merma:    {resumen.get('total_merma_kg', 0):,.2f} kg  |  {resumen.get('pct_merma', 0):.2f}%")
print(f"   Stock T:  ${resumen.get('total_stock_teorico_valor', 0):,.2f}")

# Análisis por año
por_anio = resultado.get('por_anio', {})

for anio in sorted(por_anio.keys()):
    datos_anio = por_anio[anio]
    
    print(f"\n\n{'=' * 140}")
    print(f"TEMPORADA {anio} ({datos_anio.get('temporada', '')})")
    print(f"Período: {datos_anio.get('fecha_desde')} a {datos_anio.get('fecha_hasta')}")
    print("=" * 140)
    
    datos = datos_anio.get('datos', [])
    
    if not datos:
        print("\n⚠️  NO SE ENCONTRARON DATOS PARA ESTE PERÍODO")
        continue
    
    # Calcular totales del año
    total_compras_kg = sum(d.get('compras_kg', 0) for d in datos)
    total_compras_valor = sum(d.get('compras_monto', 0) for d in datos)
    total_ventas_kg = sum(d.get('ventas_kg', 0) for d in datos)
    total_ventas_valor = sum(d.get('ventas_monto', 0) for d in datos)
    total_merma_kg = sum(d.get('merma_kg', 0) for d in datos)
    
    print(f"\n📊 RESUMEN DEL AÑO:")
    print(f"   Compras:  {total_compras_kg:,.2f} kg  |  ${total_compras_valor:,.2f}  |  ${(total_compras_valor/total_compras_kg if total_compras_kg > 0 else 0):,.2f}/kg")
    print(f"   Ventas:   {total_ventas_kg:,.2f} kg  |  ${total_ventas_valor:,.2f}  |  ${(total_ventas_valor/total_ventas_kg if total_ventas_kg > 0 else 0):,.2f}/kg")
    print(f"   Merma:    {total_merma_kg:,.2f} kg  |  {(total_merma_kg/total_compras_kg*100 if total_compras_kg > 0 else 0):.2f}%")
    
    # Top 5 por volumen de compras
    datos_ordenados = sorted(datos, key=lambda x: x.get('compras_kg', 0), reverse=True)
    
    print(f"\n📋 TOP 5 POR VOLUMEN DE COMPRAS:")
    print(f"{'#':<3} {'Tipo Fruta':<20} {'Manejo':<15} {'Compras (kg)':>15} {'Ventas (kg)':>15} {'Merma (kg)':>15} {'Merma %':>10}")
    print("-" * 140)
    
    for i, dato in enumerate(datos_ordenados[:5]):
        tipo = dato.get('tipo_fruta', 'Sin tipo')
        manejo = dato.get('manejo', 'Sin manejo')
        compras_kg = dato.get('compras_kg', 0)
        ventas_kg = dato.get('ventas_kg', 0)
        merma_kg = dato.get('merma_kg', 0)
        pct_merma = dato.get('pct_merma', 0)
        
        print(f"{i+1:<3} {tipo:<20} {manejo:<15} {compras_kg:>15,.2f} {ventas_kg:>15,.2f} {merma_kg:>15,.2f} {pct_merma:>9.2f}%")
    
    # Detalle completo
    print(f"\n📊 DETALLE COMPLETO POR TIPO Y MANEJO:")
    print(f"{'Tipo Fruta':<25} {'Manejo':<15} {'Compras (kg)':>15} {'$ Compras':>18} {'Ventas (kg)':>15} {'$ Ventas':>18} {'Merma %':>10}")
    print("-" * 140)
    
    for dato in sorted(datos, key=lambda x: (x.get('tipo_fruta', ''), x.get('manejo', ''))):
        tipo = dato.get('tipo_fruta', 'Sin tipo')
        manejo = dato.get('manejo', 'Sin manejo')
        compras_kg = dato.get('compras_kg', 0)
        compras_valor = dato.get('compras_monto', 0)
        ventas_kg = dato.get('ventas_kg', 0)
        ventas_valor = dato.get('ventas_monto', 0)
        pct_merma = dato.get('pct_merma', 0)
        
        print(f"{tipo:<25} {manejo:<15} {compras_kg:>15,.2f} ${compras_valor:>17,.2f} {ventas_kg:>15,.2f} ${ventas_valor:>17,.2f} {pct_merma:>9.2f}%")
    
    # Distribución por tipo de fruta
    tipos_totales = {}
    for dato in datos:
        tipo = dato.get('tipo_fruta', 'Sin tipo')
        if tipo not in tipos_totales:
            tipos_totales[tipo] = {'compras_kg': 0, 'ventas_kg': 0, 'compras_valor': 0}
        tipos_totales[tipo]['compras_kg'] += dato.get('compras_kg', 0)
        tipos_totales[tipo]['ventas_kg'] += dato.get('ventas_kg', 0)
        tipos_totales[tipo]['compras_valor'] += dato.get('compras_monto', 0)
    
    print(f"\n🍓 DISTRIBUCIÓN POR TIPO DE FRUTA:")
    print(f"{'Tipo':<25} {'Compras (kg)':>15} {'% del Total':>12} {'$ Compras':>18} {'Ventas (kg)':>15}")
    print("-" * 140)
    
    for tipo, totales in sorted(tipos_totales.items(), key=lambda x: -x[1]['compras_kg']):
        pct = (totales['compras_kg'] / total_compras_kg * 100) if total_compras_kg > 0 else 0
        print(f"{tipo:<25} {totales['compras_kg']:>15,.2f} {pct:>11.1f}% ${totales['compras_valor']:>17,.2f} {totales['ventas_kg']:>15,.2f}")
    
    # Distribución por manejo
    manejos_totales = {}
    for dato in datos:
        manejo = dato.get('manejo', 'Sin manejo')
        if manejo not in manejos_totales:
            manejos_totales[manejo] = {'compras_kg': 0, 'ventas_kg': 0, 'compras_valor': 0}
        manejos_totales[manejo]['compras_kg'] += dato.get('compras_kg', 0)
        manejos_totales[manejo]['ventas_kg'] += dato.get('ventas_kg', 0)
        manejos_totales[manejo]['compras_valor'] += dato.get('compras_monto', 0)
    
    print(f"\n🌱 DISTRIBUCIÓN POR TIPO DE MANEJO:")
    print(f"{'Manejo':<25} {'Compras (kg)':>15} {'% del Total':>12} {'$ Compras':>18} {'Ventas (kg)':>15}")
    print("-" * 140)
    
    for manejo, totales in sorted(manejos_totales.items(), key=lambda x: -x[1]['compras_kg']):
        pct = (totales['compras_kg'] / total_compras_kg * 100) if total_compras_kg > 0 else 0
        print(f"{manejo:<25} {totales['compras_kg']:>15,.2f} {pct:>11.1f}% ${totales['compras_valor']:>17,.2f} {totales['ventas_kg']:>15,.2f}")

# Comparativa entre años
if len(ANIOS) > 1:
    print(f"\n\n{'=' * 140}")
    print("COMPARATIVA ENTRE TEMPORADAS")
    print("=" * 140)
    
    print(f"\n{'Temporada':<12} {'Compras (kg)':>15} {'$ Compras':>18} {'Ventas (kg)':>15} {'$ Ventas':>18} {'Merma %':>10}")
    print("-" * 140)
    
    for anio in sorted(por_anio.keys()):
        datos = por_anio[anio].get('datos', [])
        
        total_compras_kg = sum(d.get('compras_kg', 0) for d in datos)
        total_compras_valor = sum(d.get('compras_monto', 0) for d in datos)
        total_ventas_kg = sum(d.get('ventas_kg', 0) for d in datos)
        total_ventas_valor = sum(d.get('ventas_monto', 0) for d in datos)
        total_merma_kg = sum(d.get('merma_kg', 0) for d in datos)
        pct_merma = (total_merma_kg / total_compras_kg * 100) if total_compras_kg > 0 else 0
        
        print(f"{anio:<12} {total_compras_kg:>15,.2f} ${total_compras_valor:>17,.2f} {total_ventas_kg:>15,.2f} ${total_ventas_valor:>17,.2f} {pct_merma:>9.2f}%")

print("\n" + "=" * 140)
print("DEBUG COMPLETADO")
print("=" * 140)
