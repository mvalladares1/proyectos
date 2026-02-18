"""
Script para validar que las sumas del concepto 1.2.1 cuadren correctamente.
Verifica que los totales de cada categoría sumen correctamente.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.flujo_caja.real_proyectado import RealProyectadoCalculator
from shared.odoo_client import OdooClient
from collections import defaultdict

def format_money(value):
    """Formatea un número como moneda chilena."""
    if value < 0:
        return f"-${abs(value):,.0f}".replace(',', '.')
    return f"${value:,.0f}".replace(',', '.')

def main():
    print("\n" + "="*80)
    print("VALIDACIÓN DE SUMAS - CONCEPTO 1.2.1 PAGOS PROVEEDORES")
    print("Verificando que los números cuadren correctamente")
    print("="*80 + "\n")
    
    # Inicializar servicio
    odoo = OdooClient()
    service = RealProyectadoCalculator(odoo)
    
    # Período de análisis (ENE-FEB 2026)
    fecha_inicio = '2026-01-01'
    fecha_fin = '2026-02-28'
    
    print(f"Período de análisis: {fecha_inicio} a {fecha_fin}\n")
    
    # Obtener datos
    resultado = service.calcular_pagos_proveedores(fecha_inicio, fecha_fin)
    
    print("TOTALES GENERALES:")
    print("-" * 80)
    print(f"REAL TOTAL:       {format_money(resultado['real'])}")
    print(f"PROYECTADO TOTAL: {format_money(resultado['proyectado'])}")
    print(f"MONTO TOTAL:      {format_money(resultado.get('total', resultado['real'] + resultado['proyectado']))}")
    print(f"Facturas procesadas: {resultado.get('facturas_count', 'N/A')}")
    print()
    
    # Extraer categorías
    categorias = {}
    suma_real_categorias = 0
    suma_proyectado_categorias = 0
    suma_monto_categorias = 0
    
    for cuenta in resultado.get('cuentas', []):
        codigo = cuenta.get('codigo', '')
        nombre = cuenta.get('nombre', '')
        
        # Usar el código como identificador único
        categoria = codigo.upper()
        
        # Determinar ícono por nombre
        if '✅' in nombre:
            icono = '✅'
        elif '⏳' in nombre:
            icono = '⏳'
        elif '❌' in nombre:
            icono = '❌'
        elif '💚' in nombre:
            icono = '💚'
        elif '💛' in nombre:
            icono = '💛'
        elif '🔄' in nombre:
            icono = '🔄'
        else:
            icono = '📊'
        
        real = cuenta.get('real', 0)
        proyectado = cuenta.get('proyectado', 0)
        monto = cuenta.get('monto', 0)
        
        categorias[categoria] = {
            'icono': icono,
            'nombre': nombre,
            'real': real,
            'proyectado': proyectado,
            'monto': monto,
            'proveedores': len(cuenta.get('etiquetas', []))
        }
        
        suma_real_categorias += real
        suma_proyectado_categorias += proyectado
        suma_monto_categorias += monto
    
    print("\nDETALLE POR CATEGORÍA:")
    print("=" * 80)
    
    for cat_name, data in categorias.items():
        print(f"\n{data['icono']} {cat_name}:")
        print(f"  REAL:       {format_money(data['real'])}")
        print(f"  PROYECTADO: {format_money(data['proyectado'])}")
        print(f"  MONTO:      {format_money(data['monto'])}")
        print(f"  Proveedores: {data['proveedores']}")
    
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE SUMAS:")
    print("-" * 80)
    print(f"Suma REAL categorías:       {format_money(suma_real_categorias)}")
    print(f"REAL total reportado:       {format_money(resultado['real'])}")
    print(f"Diferencia REAL:            {format_money(suma_real_categorias - resultado['real'])}")
    print()
    print(f"Suma PROYECTADO categorías: {format_money(suma_proyectado_categorias)}")
    print(f"PROYECTADO total reportado: {format_money(resultado['proyectado'])}")
    print(f"Diferencia PROYECTADO:      {format_money(suma_proyectado_categorias - resultado['proyectado'])}")
    print()
    total_reportado = resultado.get('total', resultado['real'] + resultado['proyectado'])
    print(f"Suma MONTO categorías:      {format_money(suma_monto_categorias)}")
    print(f"MONTO total reportado:      {format_money(total_reportado)}")
    print(f"Diferencia MONTO:           {format_money(suma_monto_categorias - total_reportado)}")
    
    # Validación
    print("\n" + "=" * 80)
    TOLERANCIA = 1.0  # 1 peso de tolerancia por redondeo
    total_reportado = resultado.get('total', resultado['real'] + resultado['proyectado'])
    
    if abs(suma_real_categorias - resultado['real']) < TOLERANCIA:
        print("✅ REAL: Las sumas cuadran correctamente")
    else:
        print("❌ REAL: HAY DISCREPANCIA EN LAS SUMAS")
    
    if abs(suma_proyectado_categorias - resultado['proyectado']) < TOLERANCIA:
        print("✅ PROYECTADO: Las sumas cuadran correctamente")
    else:
        print("❌ PROYECTADO: HAY DISCREPANCIA EN LAS SUMAS")
    
    if abs(suma_monto_categorias - total_reportado) < TOLERANCIA:
        print("✅ MONTO: Las sumas cuadran correctamente")
    else:
        print("❌ MONTO: HAY DISCREPANCIA EN LAS SUMAS")
    
    # Verificar consistencia REAL + PROYECTADO = MONTO
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE CONSISTENCIA (REAL + PROYECTADO = MONTO):")
    print("-" * 80)
    
    for cat_name, data in categorias.items():
        calculado = data['real'] + data['proyectado']
        diff = calculado - data['monto']
        if abs(diff) < TOLERANCIA:
            print(f"✅ {cat_name}: {format_money(data['real'])} + {format_money(data['proyectado'])} = {format_money(data['monto'])}")
        else:
            print(f"❌ {cat_name}: {format_money(data['real'])} + {format_money(data['proyectado'])} = {format_money(calculado)} ≠ {format_money(data['monto'])} (diff: {format_money(diff)})")
    
    # Total general
    total_reportado = resultado.get('total', resultado['real'] + resultado['proyectado'])
    total_calculado = resultado['real'] + resultado['proyectado']
    diff_total = total_calculado - total_reportado
    if abs(diff_total) < TOLERANCIA:
        print(f"✅ TOTAL: {format_money(resultado['real'])} + {format_money(resultado['proyectado'])} = {format_money(total_reportado)}")
    else:
        print(f"❌ TOTAL: {format_money(resultado['real'])} + {format_money(resultado['proyectado'])} = {format_money(total_calculado)} ≠ {format_money(total_reportado)} (diff: {format_money(diff_total)})")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
