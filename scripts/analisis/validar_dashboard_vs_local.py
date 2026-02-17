"""
Script para validar que los números del dashboard coincidan con nuestros cálculos.
Compara los valores mostrados en DEV con los calculados localmente.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.flujo_caja.real_proyectado import RealProyectadoCalculator
from shared.odoo_client import OdooClient

def format_money(value):
    """Formatea un número como moneda chilena."""
    if value < 0:
        return f"-${abs(value):,.0f}".replace(',', '.')
    return f"${value:,.0f}".replace(',', '.')

def main():
    print("\n" + "="*100)
    print("VALIDACIÓN DE NÚMEROS DEL DASHBOARD vs CÁLCULOS LOCALES")
    print("="*100 + "\n")
    
    # Valores del dashboard (de las imágenes)
    dashboard_valores = {
        'TOTAL_REAL': -4309489573,
        'TOTAL_PROYECTADO': -651107937,
        'TOTAL_MONTO': -4960597510,
        'PAGADAS_REAL': -4419059560,
        'PAGADAS_PROYECTADO': 0,
        'PAGADAS_TOTAL': -4419059560,
        'PARCIALES_REAL': -546374152,
        'PARCIALES_PROYECTADO': -552503938,
        'PARCIALES_TOTAL': -1098878090,
        'NO_PAGADAS_REAL': 0,
        'NO_PAGADAS_PROYECTADO': -98603999,
        'NO_PAGADAS_TOTAL': -98603999,
        'NC_DEVUELTAS_REAL': 652552639,
        'NC_DEVUELTAS_PROYECTADO': 0,
        'NC_DEVUELTAS_TOTAL': 652552639,
        'NC_PARCIALES_REAL': 3391500,
        'NC_PARCIALES_PROYECTADO': 0,
        'NC_PARCIALES_TOTAL': 3391500
    }
    
    # Calcular localmente
    odoo = OdooClient()
    service = RealProyectadoCalculator(odoo)
    resultado = service.calcular_pagos_proveedores('2026-01-01', '2026-02-28')
    
    # Extraer valores locales
    locales_valores = {
        'TOTAL_REAL': resultado['real'],
        'TOTAL_PROYECTADO': resultado['proyectado'],
        'TOTAL_MONTO': resultado.get('total', resultado['real'] + resultado['proyectado'])
    }
    
    for cuenta in resultado.get('cuentas', []):
        codigo = cuenta.get('codigo', '').upper()
        locales_valores[f'{codigo}_REAL'] = cuenta.get('real', 0)
        locales_valores[f'{codigo}_PROYECTADO'] = cuenta.get('proyectado', 0)
        locales_valores[f'{codigo}_TOTAL'] = cuenta.get('monto', 0)
    
    # Comparar
    print("COMPARACIÓN DETALLADA:")
    print("="*100)
    print(f"{'CONCEPTO':<30} {'DASHBOARD':>20} {'LOCAL':>20} {'DIFERENCIA':>20} {'STATUS':>10}")
    print("-"*100)
    
    todas_match = True
    TOLERANCIA = 1.0
    
    categorias_orden = [
        ('TOTAL', 'TOTALES GENERALES'),
        ('PAGADAS', '✅ Facturas Pagadas'),
        ('PARCIALES', '⏳ Facturas Parciales'),
        ('NO_PAGADAS', '❌ Facturas No Pagadas'),
        ('NC_DEVUELTAS', '💚 N/C Devueltas'),
        ('NC_PARCIALES', '💛 N/C Parciales')
    ]
    
    for categoria_key, categoria_nombre in categorias_orden:
        print(f"\n{categoria_nombre}:")
        print("-"*100)
        
        for tipo in ['REAL', 'PROYECTADO', 'TOTAL']:
            key = f'{categoria_key}_{tipo}'
            
            if key not in dashboard_valores:
                continue
            
            dashboard_val = dashboard_valores.get(key, 0)
            local_val = locales_valores.get(key, 0)
            diferencia = local_val - dashboard_val
            
            if abs(diferencia) < TOLERANCIA:
                status = "✅ OK"
            else:
                status = "❌ DIFF"
                todas_match = False
            
            concepto = f"  {tipo}"
            print(f"{concepto:<30} {format_money(dashboard_val):>20} {format_money(local_val):>20} {format_money(diferencia):>20} {status:>10}")
    
    # Resumen
    print("\n" + "="*100)
    print("RESUMEN DE VALIDACIÓN:")
    print("="*100)
    
    if todas_match:
        print("✅ TODOS LOS VALORES COINCIDEN PERFECTAMENTE")
        print("   El dashboard DEV está mostrando los números correctos.")
    else:
        print("❌ HAY DIFERENCIAS ENTRE DASHBOARD Y CÁLCULOS LOCALES")
        print("   Revisar las discrepancias arriba.")
    
    # Verificación adicional: sumar categorías
    print("\n" + "="*100)
    print("VERIFICACIÓN DE SUMA DE CATEGORÍAS:")
    print("="*100)
    
    suma_real = (
        locales_valores.get('PAGADAS_REAL', 0) +
        locales_valores.get('PARCIALES_REAL', 0) +
        locales_valores.get('NO_PAGADAS_REAL', 0) +
        locales_valores.get('NC_DEVUELTAS_REAL', 0) +
        locales_valores.get('NC_PARCIALES_REAL', 0) +
        locales_valores.get('NC_PENDIENTES_REAL', 0)
    )
    
    suma_proyectado = (
        locales_valores.get('PAGADAS_PROYECTADO', 0) +
        locales_valores.get('PARCIALES_PROYECTADO', 0) +
        locales_valores.get('NO_PAGADAS_PROYECTADO', 0) +
        locales_valores.get('NC_DEVUELTAS_PROYECTADO', 0) +
        locales_valores.get('NC_PARCIALES_PROYECTADO', 0) +
        locales_valores.get('NC_PENDIENTES_PROYECTADO', 0)
    )
    
    print(f"Suma REAL de categorías:     {format_money(suma_real)}")
    print(f"REAL total reportado:        {format_money(locales_valores['TOTAL_REAL'])}")
    print(f"Diferencia:                  {format_money(suma_real - locales_valores['TOTAL_REAL'])}")
    print()
    print(f"Suma PROYECTADO de categorías: {format_money(suma_proyectado)}")
    print(f"PROYECTADO total reportado:    {format_money(locales_valores['TOTAL_PROYECTADO'])}")
    print(f"Diferencia:                    {format_money(suma_proyectado - locales_valores['TOTAL_PROYECTADO'])}")
    
    if abs(suma_real - locales_valores['TOTAL_REAL']) < TOLERANCIA:
        print("\n✅ REAL: La suma de categorías coincide con el total")
    else:
        print("\n❌ REAL: Hay discrepancia entre suma de categorías y total")
    
    if abs(suma_proyectado - locales_valores['TOTAL_PROYECTADO']) < TOLERANCIA:
        print("✅ PROYECTADO: La suma de categorías coincide con el total")
    else:
        print("❌ PROYECTADO: Hay discrepancia entre suma de categorías y total")
    
    print("\n" + "="*100 + "\n")

if __name__ == "__main__":
    main()
