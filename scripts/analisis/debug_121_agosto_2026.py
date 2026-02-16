#!/usr/bin/env python3
"""
Script para debuggear datos de 1.2.1 hasta agosto 2026
Muestra desglose de facturas PARCIALES y NO_PAGADAS
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shared.odoo_client import OdooClient
from backend.services.flujo_caja.real_proyectado import RealProyectadoCalculator
from datetime import datetime, timedelta
import json

def format_money(value):
    """Formato chileno con punto como separador de miles"""
    if value == 0:
        return "$0"
    sign = "-" if value < 0 else ""
    abs_value = abs(value)
    return f"{sign}${abs_value:,.0f}".replace(",", ".")

def main():
    print("\n" + "="*100)
    print("DEBUG: 1.2.1 PAGOS PROVEEDORES - HASTA AGOSTO 2026")
    print("="*100)
    
    # Inicializar servicio
    odoo = OdooClient()
    service = RealProyectadoCalculator(odoo)
    
    # Meses hasta agosto 2026
    meses = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"]
    fecha_inicio = "2026-01-01"
    fecha_fin = "2026-08-31"
    
    # Obtener resultado
    resultado = service.calcular_pagos_proveedores(fecha_inicio, fecha_fin, meses)
    
    print(f"\nTOTAL GENERAL: {format_money(resultado['total'])}")
    print(f"Facturas procesadas: {resultado.get('facturas_count', 0)}")
    
    # Buscar cuentas que corresponden a parciales o no_pagadas
    cuentas = resultado.get('cuentas', [])
    
    print(f"\nTotal de cuentas encontradas: {len(cuentas)}")
    
    # Agrupar cuentas por estado (usando emoji)
    estados_encontrados = {
        'PARCIALES': [],
        'NO_PAGADAS': []
    }
    
    iconos = {
        'PARCIALES': '⏳',
        'NO_PAGADAS': '❌'
    }
    
    for cuenta in cuentas:
        nombre = cuenta.get('nombre', '')
        if '⏳' in nombre:
            estados_encontrados['PARCIALES'].append(cuenta)
        elif '❌' in nombre:
            estados_encontrados['NO_PAGADAS'].append(cuenta)
    
    # Mostrar información por estado
    for estado_key, cuentas_estado in estados_encontrados.items():
        if not cuentas_estado:
            continue
            
        icono = iconos[estado_key]
        total_estado = sum(c.get('monto', 0) for c in cuentas_estado)
        
        print("\n" + "="*100)
        print(f"ESTADO: {icono} Facturas {estado_key.title()}")
        print(f"MONTO TOTAL: {format_money(total_estado)}")
        print(f"Categorías encontradas: {len(cuentas_estado)}")
        print("="*100)
        
        # Mostrar top 5 categorías
        for idx, cuenta in enumerate(sorted(cuentas_estado, key=lambda x: abs(x.get('monto', 0)), reverse=True)[:5], 1):
            cat_nombre = cuenta.get('nombre', '').replace(icono, '').strip()
            cat_monto = cuenta.get('monto', 0)
            etiquetas = cuenta.get('etiquetas', [])
            
            print(f"\n  📁 CATEGORÍA {idx}: {cat_nombre}")
            print(f"     Monto: {format_money(cat_monto)}")
            print(f"     Proveedores: {len(etiquetas)}")
            
            # Mostrar top 5 proveedores
            if etiquetas:
                print(f"\n     Top 5 proveedores:")
                for prov_idx, prov in enumerate(etiquetas[:5], 1):
                    prov_nombre = prov.get('nombre', '')
                    prov_monto = prov.get('monto', 0)
                    montos_por_mes = prov.get('montos_por_mes', {})
                    
                    # Contar cuántos meses tienen montos
                    meses_con_monto = sum(1 for m in montos_por_mes.values() if m != 0)
                    
                    print(f"     {prov_idx}. {prov_nombre[:45]:<45} | Monto: {format_money(prov_monto):>18} | Meses: {meses_con_monto}")
                    
                    # Mostrar primeros 3 meses con montos
                    meses_info = [(mes, monto) for mes, monto in sorted(montos_por_mes.items()) if monto != 0][:3]
                    for mes, monto in meses_info:
                        print(f"        - {mes}: {format_money(monto)}")
    
    print("\n" + "="*100)
    print("FIN DEBUG")
    print("="*100 + "\n")

if __name__ == "__main__":
    main()
