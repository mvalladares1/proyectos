#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificar qué campos de defectos tienen datos en quality checks IQF/BLOCK
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
    print("ANALIZANDO CAMPOS EN QUALITY CHECKS CON CLASIFICACIÓN IQF/BLOCK")
    print("="*80)
    
    # Buscar quality checks con clasificación IQF o BLOCK que tengan defectos
    # Leer solo campos específicos para evitar timeout
    campos_leer = ['id', 'x_studio_calific_final', 'x_studio_total_iqf_', 'x_studio_total_block_',
                   'x_studio_total_def_calidad', 'x_studio_total_def_calidad_1',
                   'x_studio_hongos', 'x_studio_inmadura', 'x_studio_sobremadura',
                   'x_studio_deshidratado', 'x_studio_crumble', 'x_studio_dao_mecanico',
                   'x_studio_frutos_deformes', 'x_studio_fruta_verde',
                   'x_studio_heridapartidamolida', 'x_studio_materias_extraas',
                   'x_studio_hongos_1_porcentaje', 'x_studio_inmadura_1_porcentaje',
                   'x_studio_sobremadurez_1_porcentaje', 'x_studio_deshidratado_porcentaje',
                   'x_studio_dao_mecanico_porcentaje', 'x_studio_presencia_de_insectos_1_porcentaje',
                   'x_studio_heridapartidamolida_porcentaje', 'x_studio_materias_extraas_1_porcentaje']
    
    qcs = odoo.search_read(
        'quality.check',
        [('x_studio_calific_final', 'in', ['IQF', 'BLOCK'])],
        campos_leer,
        limit=50
    )
    
    print(f"\nTotal quality checks IQF/BLOCK: {len(qcs)}")
    
    # Analizar qué campos están presentes
    campos_con_datos = {}
    
    for qc in qcs:
        for campo, valor in qc.items():
            if 'studio' in campo and valor not in [None, False, 0, '', []]:
                if campo not in campos_con_datos:
                    campos_con_datos[campo] = 0
                campos_con_datos[campo] += 1
    
    print("\nCampos con datos (ordenados por frecuencia):")
    print(f"{'Campo':<60s} | Cantidad")
    print("-" * 80)
    for campo, count in sorted(campos_con_datos.items(), key=lambda x: x[1], reverse=True):
        if any(word in campo.lower() for word in ['defect', 'hongos', 'inmadura', 'sobremadura', 
                                                    'deshidratado', 'crumble', 'mecanico', 'insecto',
                                                    'deformes', 'verde', 'herida', 'partida', 'materias']):
            print(f"{campo:<60s} | {count}")
    
    # Ahora mostrar un ejemplo de quality check con datos
    print("\n" + "="*80)
    print("EJEMPLO DE QUALITY CHECK CON DATOS (ID 1304)")
    print("="*80)
    
    qc_ejemplo = odoo.search_read(
        'quality.check',
        [('id', '=', 1304)],
        limit=1
    )
    
    if qc_ejemplo:
        print("\nCampos en gramos:")
        for campo, valor in sorted(qc_ejemplo[0].items()):
            if 'studio' in campo and 'porcentaje' not in campo and valor not in [None, False, 0, '', []]:
                if any(word in campo.lower() for word in ['defect', 'hongos', 'inmadura', 'sobremadura', 
                                                            'deshidratado', 'crumble', 'mecanico', 'insecto',
                                                            'deformes', 'verde', 'herida', 'partida', 'materias',
                                                            'total', 'iqf', 'block']):
                    print(f"  {campo}: {valor}")
        
        print("\nCampos en porcentaje:")
        for campo, valor in sorted(qc_ejemplo[0].items()):
            if 'studio' in campo and 'porcentaje' in campo and valor not in [None, False, 0, '', []]:
                print(f"  {campo}: {valor}")

if __name__ == "__main__":
    main()
