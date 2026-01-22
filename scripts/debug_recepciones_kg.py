"""
Script para diagnosticar diferencias de Kg entre KPIs y Calidad.

Este script compara los kg reportados en diferentes secciones para identificar
de dónde vienen las diferencias.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient
from datetime import datetime, timedelta

# Configurar credenciales
USERNAME = "user@riofuturo.cl"  # Cambiar por tus credenciales
PASSWORD = "tu_password"  # Cambiar por tu password

# Rango de fechas a analizar
FECHA_DESDE = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
FECHA_HASTA = datetime.now().strftime("%Y-%m-%d")

print("=" * 100)
print("DIAGNÓSTICO DE DIFERENCIAS DE KG EN RECEPCIONES")
print("=" * 100)
print(f"Período: {FECHA_DESDE} hasta {FECHA_HASTA}")
print("=" * 100)

# Conectar a Odoo
odoo = OdooClient(username=USERNAME, password=PASSWORD)

# IDs de picking types por origen
ORIGEN_PICKING_MAP = {
    "RFP": 1,
    "VILKUN": 217,
    "SAN JOSE": 164
}

# 1. Obtener TODAS las recepciones por origen
print("\n📦 RECEPCIONES POR ORIGEN (solo estado done):")
print("-" * 100)

total_kg_global = 0
total_kg_mp_global = 0
total_kg_bandejas_global = 0

for origen, picking_type_id in ORIGEN_PICKING_MAP.items():
    # Buscar recepciones
    recepciones = odoo.search_read(
        'stock.picking',
        [
            ('picking_type_id', '=', picking_type_id),
            ('x_studio_categora_de_producto', '=', 'MP'),
            ('scheduled_date', '>=', FECHA_DESDE),
            ('scheduled_date', '<=', FECHA_HASTA),
            ('state', '=', 'done')
        ],
        ['id', 'name', 'scheduled_date'],
        limit=5000
    )
    
    print(f"\n{origen}:")
    print(f"  Total recepciones: {len(recepciones)}")
    
    if not recepciones:
        continue
    
    # Para cada recepción, obtener movimientos
    picking_ids = [r['id'] for r in recepciones]
    
    movimientos = odoo.search_read(
        'stock.move',
        [
            ('picking_id', 'in', picking_ids),
            ('state', '=', 'done')
        ],
        ['id', 'product_id', 'quantity_done', 'picking_id'],
        limit=50000
    )
    
    print(f"  Total movimientos: {len(movimientos)}")
    
    # Obtener productos para clasificar MP vs BANDEJAS
    product_ids = list(set([m['product_id'][0] for m in movimientos if m.get('product_id')]))
    
    productos = odoo.search_read(
        'product.product',
        [('id', 'in', product_ids)],
        ['id', 'categ_id'],
        limit=10000
    )
    
    # Mapear categorías
    categorias_map = {}
    for p in productos:
        categ = p.get('categ_id')
        categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
        categorias_map[p['id']] = categ_name
    
    # Sumar kg por categoría
    kg_mp = 0
    kg_bandejas = 0
    kg_otros = 0
    
    for m in movimientos:
        prod_id = m.get('product_id', [None])[0]
        if not prod_id:
            continue
        
        qty = m.get('quantity_done', 0) or 0
        categ = categorias_map.get(prod_id, '')
        
        if 'BANDEJ' in categ.upper():
            kg_bandejas += qty
        elif 'PRODUCTOS' in categ.upper():
            kg_mp += qty
        else:
            kg_otros += qty
    
    kg_total = kg_mp + kg_bandejas + kg_otros
    
    print(f"  Kg MP:          {kg_mp:>15,.2f}")
    print(f"  Kg Bandejas:    {kg_bandejas:>15,.2f}")
    print(f"  Kg Otros:       {kg_otros:>15,.2f}")
    print(f"  Kg TOTAL:       {kg_total:>15,.2f}")
    
    total_kg_global += kg_total
    total_kg_mp_global += kg_mp
    total_kg_bandejas_global += kg_bandejas

print("\n" + "=" * 100)
print("RESUMEN GLOBAL:")
print("=" * 100)
print(f"Total Kg MP (sin bandejas):  {total_kg_mp_global:>15,.2f}")
print(f"Total Kg Bandejas:           {total_kg_bandejas_global:>15,.2f}")
print(f"Total Kg GLOBAL:             {total_kg_global:>15,.2f}")
print("=" * 100)

# 2. Verificar recepciones en estado diferente a 'done'
print("\n\n🔍 RECEPCIONES EN OTROS ESTADOS (NO DONE):")
print("-" * 100)

for origen, picking_type_id in ORIGEN_PICKING_MAP.items():
    recepciones_otros = odoo.search_read(
        'stock.picking',
        [
            ('picking_type_id', '=', picking_type_id),
            ('x_studio_categora_de_producto', '=', 'MP'),
            ('scheduled_date', '>=', FECHA_DESDE),
            ('scheduled_date', '<=', FECHA_HASTA),
            ('state', '!=', 'done')
        ],
        ['id', 'name', 'scheduled_date', 'state'],
        limit=5000
    )
    
    if recepciones_otros:
        print(f"\n{origen}: {len(recepciones_otros)} recepciones NO DONE")
        estados = {}
        for r in recepciones_otros:
            estado = r.get('state', 'unknown')
            if estado not in estados:
                estados[estado] = 0
            estados[estado] += 1
        
        for estado, count in estados.items():
            print(f"  - {estado}: {count}")

print("\n\n✅ DIAGNÓSTICO COMPLETADO")
print("=" * 100)
print("\nCOMPARACIÓN:")
print("  - Si el total de KPIs coincide con 'Total Kg MP', entonces la diferencia es por BANDEJAS")
print("  - Si no coincide, verifica:")
print("    1. Rango de fechas (KPIs vs este script)")
print("    2. Filtros de origen (RFP + VILKÚN + SAN JOSE)")
print("    3. Recepciones excluidas de valorización")
print("    4. Estado de recepciones (done vs otros)")
print("=" * 100)
