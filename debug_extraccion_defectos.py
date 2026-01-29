#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug: Ver qué datos se están extrayendo del quality check
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from shared.odoo_client import OdooClient

def main():
    odoo = OdooClient()
    
    # Obtener campos de quality.check
    print("\n" + "="*80)
    print("OBTENIENDO CAMPOS DE QUALITY.CHECK")
    print("="*80)
    
    campos_quality = odoo.execute('quality.check', 'fields_get', [], {'attributes': ['string', 'type']})
    
    print("\nCampos relacionados con defectos:")
    defect_fields = [k for k in campos_quality.keys() if any(word in k.lower() for word in 
                    ['defecto', 'hongos', 'inmadura', 'sobremadura', 'deshidratado', 'crumble', 
                     'mecánico', 'insecto', 'deformes', 'verde', 'herida', 'partida', 'molida', 
                     'materias', 'extrañas', 'dao'])]
    
    for field in sorted(defect_fields):
        print(f"  {field}: {campos_quality[field].get('string', 'N/A')}")
    
    # Ahora simular la determinación de campos como lo hace el servicio
    def _determinar_campo(campos_dict, opciones):
        """Determina qué campo usar de una lista de opciones."""
        for opcion in opciones:
            if opcion in campos_dict:
                return opcion
        return None
    
    print("\n" + "="*80)
    print("DETERMINANDO CAMPOS A USAR (como en el servicio)")
    print("="*80)
    
    campos_quality_usar = {
        'pallet': _determinar_campo(campos_quality, ['x_studio_n_de_palet_o_paquete', 'x_studio_n_palet']),
        'clasificacion': _determinar_campo(campos_quality, ['x_studio_calific_final', 'x_studio_calificacin_final']),
        'total_defectos': _determinar_campo(campos_quality, ['x_studio_total_def_calidad', 'x_studio_total_de_defectos_']),
        'temperatura': _determinar_campo(campos_quality, ['x_studio_temperatura']),
        'hongos': _determinar_campo(campos_quality, ['x_studio_hongos']),
        'inmadura': _determinar_campo(campos_quality, ['x_studio_inmadura']),
        'sobremadura': _determinar_campo(campos_quality, ['x_studio_sobremadura', 'x_studio_sobre_madura']),
        'deshidratado': _determinar_campo(campos_quality, ['x_studio_deshidratado']),
        'crumble': _determinar_campo(campos_quality, ['x_studio_crumble']),
        'dano_mecanico': _determinar_campo(campos_quality, ['x_studio_dao_mecanico', 'x_studio_dano_mecanico']),
        'dano_insecto': _determinar_campo(campos_quality, ['x_studio_presencia_de_insectos', 'x_studio_totdaoinsecto', 'x_studio_dao_insecto']),
        'deformes': _determinar_campo(campos_quality, ['x_studio_frutos_deformes', 'x_studio_deformes']),
        'fruta_verde': _determinar_campo(campos_quality, ['x_studio_fruta_verde']),
        'herida_partida': _determinar_campo(campos_quality, ['x_studio_heridapartidamolida', 'x_studio_heridapartiduramolida']),
        'materias_extranas': _determinar_campo(campos_quality, ['x_studio_materias_extraas', 'x_studio_materias_extranas']),
    }
    
    for key, value in campos_quality_usar.items():
        print(f"{key:20s} -> {value}")
    
    # Ahora leer un quality check real
    print("\n" + "="*80)
    print("LEYENDO QUALITY CHECK ID 8169 (el que sabemos que tiene datos)")
    print("="*80)
    
    # Construir la lista de campos a leer
    quality_campos_leer = ['id', 'picking_id', 'create_date']
    for campo in campos_quality_usar.values():
        if campo:
            quality_campos_leer.append(campo)
    
    print(f"\nCampos que se van a leer: {quality_campos_leer}")
    
    qc = odoo.search_read(
        'quality.check',
        [('id', '=', 8169)],
        quality_campos_leer
    )
    
    if qc:
        print("\nDatos del quality check:")
        for key, value in qc[0].items():
            if 'studio' in key or key in ['id', 'picking_id']:
                print(f"  {key}: {value}")
        
        # Simular la extracción de valores como lo hace el servicio
        print("\n" + "="*80)
        print("EXTRAYENDO VALORES (como en el servicio)")
        print("="*80)
        
        def _get_field(data_dict, field_name, default=''):
            """Obtiene un campo del diccionario de forma segura."""
            if not field_name:
                return default
            value = data_dict.get(field_name, default)
            return value if value else default
        
        hongos = _get_field(qc[0], campos_quality_usar.get('hongos'), 0)
        deshidratado = _get_field(qc[0], campos_quality_usar.get('deshidratado'), 0)
        deformes = _get_field(qc[0], campos_quality_usar.get('deformes'), 0)
        materias_extranas = _get_field(qc[0], campos_quality_usar.get('materias_extranas'), 0)
        total_defectos = _get_field(qc[0], campos_quality_usar.get('total_defectos'), 0)
        
        print(f"Hongos: {hongos}")
        print(f"Deshidratado: {deshidratado}")
        print(f"Deformes: {deformes}")
        print(f"Materias extrañas: {materias_extranas}")
        print(f"Total defectos: {total_defectos}")

if __name__ == "__main__":
    main()
