#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Buscar campos relacionados con IQF y BLOCK en quality.check
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from shared.odoo_client import OdooClient

def main():
    odoo = OdooClient(
        username='mvalladares@riofuturo.cl',
        password='c0766224bec30cac071ffe43a858c9ccbd521ddd'
    )
    
    print("\n" + "="*80)
    print("BUSCANDO CAMPOS DE IQF Y BLOCK EN QUALITY.CHECK")
    print("="*80)
    
    campos_quality = odoo.execute('quality.check', 'fields_get', [], {'attributes': ['string', 'type']})
    
    palabras_buscar = ['iqf', 'block', 'bloque', 'total', 'porcentaje', 'porcent']
    
    campos_encontrados = []
    for campo, info in campos_quality.items():
        campo_lower = campo.lower()
        string_lower = info.get('string', '').lower()
        
        if any(palabra in campo_lower or palabra in string_lower for palabra in palabras_buscar):
            if 'studio' in campo:
                campos_encontrados.append((campo, info.get('string', 'N/A'), info.get('type', 'N/A')))
    
    print("\nCampos encontrados:")
    for campo, string, tipo in sorted(campos_encontrados):
        print(f"  {campo:50s} | {string:30s} | {tipo}")
    
    # Buscar un quality check real para ver qué campos tienen valores
    print("\n" + "="*80)
    print("BUSCANDO QUALITY CHECK CON DATOS IQF/BLOCK")
    print("="*80)
    
    # Buscar quality checks con clasificación IQF o BLOCK
    qcs = odoo.search_read(
        'quality.check',
        [('x_studio_calific_final', 'in', ['IQF', 'BLOCK'])],
        ['id', 'x_studio_calific_final'] + [c[0] for c in campos_encontrados],
        limit=5
    )
    
    if qcs:
        print(f"\nSe encontraron {len(qcs)} quality checks con clasificación IQF/BLOCK:\n")
        for qc in qcs:
            print(f"ID: {qc['id']}, Clasificación: {qc.get('x_studio_calific_final', 'N/A')}")
            for campo, _, _ in campos_encontrados:
                valor = qc.get(campo)
                if valor not in [None, False, 0, '']:
                    print(f"  {campo}: {valor}")
            print("-" * 40)

if __name__ == "__main__":
    main()
