#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificar datos de calidad para FRUTILLA específicamente
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from shared.odoo_client import OdooClient
from datetime import datetime, timedelta

def main():
    odoo = OdooClient()
    
    print("\n" + "="*80)
    print("BÚSQUEDA DE QUALITY CHECKS PARA FRUTILLA")
    print("="*80)
    
    # Buscar quality checks de frutilla
    quality_checks = odoo.search_read(
        'quality.check',
        [('x_studio_tipo_de_fruta', '=', 'Frutilla')],
        ['name', 'id', 'x_studio_tipo_de_fruta', 'x_studio_total_def_calidad',
         'x_studio_deshidratado', 'x_studio_dao_mecanico', 'x_studio_hongos',
         'x_studio_inmadura', 'x_studio_sobremadura', 'x_studio_crumble',
         'x_studio_dao_insecto', 'x_studio_frutos_deformes', 
         'x_studio_fruta_verde', 'x_studio_heridapartidamolida',
         'x_studio_materias_extraas', 'x_studio_n_de_palet_o_paquete',
         'x_studio_calific_final'],
        limit=10
    )
    
    if not quality_checks:
        print("\nNo se encontraron quality checks para Frutilla")
        print("\nBuscando recepciones de Frutilla...")
        
        # Buscar recepciones de frutilla en los últimos 3 meses
        fecha_desde = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        picking_ids = odoo.search(
            'stock.picking',
            [('picking_type_id.name', 'in', ['Recepciones', 'Recepciones MP']),
             ('state', '=', 'done'),
             ('date_done', '>=', fecha_desde)],
            limit=100
        )
        
        print(f"Encontradas {len(picking_ids)} recepciones en total")
        
        # Revisar moves para ver si hay frutilla
        frutilla_count = 0
        for picking_id in picking_ids:
            moves = odoo.search_read(
                'stock.move',
                [('picking_id', '=', picking_id)],
                ['product_id']
            )
            
            for move in moves:
                if move['product_id']:
                    product = odoo.search_read(
                        'product.product',
                        [('id', '=', move['product_id'][0])],
                        ['name', 'categ_id']
                    )
                    
                    if product and 'frutilla' in product[0]['name'].lower():
                        frutilla_count += 1
                        print(f"\nRecepción ID {picking_id}: {product[0]['name']}")
                        
                        # Buscar quality check asociado
                        qc = odoo.search_read(
                            'quality.check',
                            [('picking_id', '=', picking_id)],
                            ['id', 'x_studio_tipo_de_fruta', 'x_studio_total_def_calidad']
                        )
                        if qc:
                            print(f"  Quality check ID: {qc[0]['id']}")
                            print(f"  Tipo fruta: {qc[0].get('x_studio_tipo_de_fruta', 'N/A')}")
                            print(f"  Total defectos: {qc[0].get('x_studio_total_def_calidad', 0)}g")
        
        print(f"\nTotal recepciones de Frutilla encontradas: {frutilla_count}")
        
    else:
        print(f"\nSe encontraron {len(quality_checks)} quality checks de Frutilla:\n")
        
        for qc in quality_checks:
            print(f"ID: {qc['id']}, Pallet: {qc.get('x_studio_n_de_palet_o_paquete', 'N/A')}")
            print(f"Clasificación: {qc.get('x_studio_calific_final', 'N/A')}")
            print(f"Total defectos: {qc.get('x_studio_total_def_calidad', 0)}g")
            print(f"  Deshidratado: {qc.get('x_studio_deshidratado', 0)}g")
            print(f"  Daño mecánico: {qc.get('x_studio_dao_mecanico', 0)}g")
            print(f"  Hongos: {qc.get('x_studio_hongos', 0)}g")
            print(f"  Inmadura: {qc.get('x_studio_inmadura', 0)}g")
            print(f"  Sobremadura: {qc.get('x_studio_sobremadura', 0)}g")
            print(f"  Crumble: {qc.get('x_studio_crumble', 0)}g")
            print(f"  Daño insecto: {qc.get('x_studio_dao_insecto', 0)}g")
            print(f"  Frutos deformes: {qc.get('x_studio_frutos_deformes', 0)}g")
            print(f"  Fruta verde: {qc.get('x_studio_fruta_verde', 0)}g")
            print(f"  Herida/Partida: {qc.get('x_studio_heridapartidamolida', 0)}g")
            print(f"  Materias extrañas: {qc.get('x_studio_materias_extraas', 0)}g")
            print("-" * 40)

if __name__ == "__main__":
    main()
