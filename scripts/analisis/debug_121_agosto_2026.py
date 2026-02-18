#!/usr/bin/env python3
"""
Script para debuggear datos de 1.2.1 hasta agosto 2026
Muestra desglose de 4 NIVELES REALES:
- Nivel 2: ESTADOS (Pagadas, Parciales, No Pagadas)
- Nivel 3: CATEGORÍAS de contacto
- Nivel 4: PROVEEDORES individuales
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
    
    # Buscar cuentas (ESTADOS)
    cuentas = resultado.get('cuentas', [])
    
    print(f"\nTotal de ESTADOS encontrados: {len(cuentas)}")
    
    for idx_estado, cuenta in enumerate(cuentas, 1):
        nombre_estado = cuenta.get('nombre', '')
        monto_estado = cuenta.get('monto', 0)
        etiquetas = cuenta.get('etiquetas', [])
        
        print("\n" + "="*100)
        print(f"NIVEL 2 - ESTADO {idx_estado}: {nombre_estado}")
        print(f"MONTO TOTAL: {format_money(monto_estado)}")
        print("="*100)
        
        if not etiquetas:
            print("⚠️ NO HAY ETIQUETAS EN ESTE ESTADO")
            continue
        
        # Las etiquetas ahora son CATEGORÍAS (nivel 3) con sub_etiquetas (proveedores nivel 4) ANIDADOS
        categorias = [e for e in etiquetas if e.get('nivel') == 3]
        
        # Contar proveedores totales
        total_proveedores = sum(len(cat.get('sub_etiquetas', [])) for cat in categorias)
        
        print(f"\nCategorías (Nivel 3): {len(categorias)}")
        print(f"Proveedores (Nivel 4): {total_proveedores}")
        
        # Mostrar top 5 categorías
        for idx_cat, cat in enumerate(categorias[:5], 1):
            cat_nombre = cat.get('nombre', '').replace('📁 ', '').strip()
            cat_monto = cat.get('monto', 0)
            
            # Obtener proveedores ANIDADOS en esta categoría
            proveedores_cat = cat.get('sub_etiquetas', [])
            
            print(f"\n  NIVEL 3 - CATEGORÍA {idx_cat}: {cat_nombre}")
            print(f"     Monto: {format_money(cat_monto)}")
            print(f"     Proveedores: {len(proveedores_cat)}")
            
            # Mostrar top 5 proveedores de esta categoría
            if proveedores_cat:
                print(f"\n     NIVEL 4 - Top 5 proveedores:")
                for prov_idx, prov in enumerate(proveedores_cat[:5], 1):
                    prov_nombre = prov.get('nombre', '').replace('↳ ', '').strip()
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
