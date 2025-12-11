"""
Script de diagnóstico para entender por qué no se captura la producción PT.
Analiza una MO específica y muestra todos los productos involucrados.
"""
import sys
import os
from datetime import datetime
from getpass import getpass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient


def get_credentials():
    print("\n📝 Ingresa las credenciales de Odoo:")
    username = input("   Usuario (email): ").strip()
    password = getpass("   API Key: ").strip()
    return username, password


def main():
    print("="*80)
    print("🔍 DIAGNÓSTICO DE RENDIMIENTO - Análisis de filtro de frutas")
    print("="*80)
    
    username, password = get_credentials()
    
    try:
        odoo = OdooClient(username=username, password=password)
        print("\n✅ Conectado a Odoo")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return
    
    # Buscar MOs de agosto 2025
    print("\n" + "="*80)
    print("1. BUSCANDO MOs EN AGOSTO 2025")
    print("="*80)
    
    mos = odoo.search_read(
        'mrp.production',
        [
            ['state', '=', 'done'],
            ['date_finished', '>=', '2025-08-01'],
            ['date_finished', '<=', '2025-08-31 23:59:59']
        ],
        ['name', 'product_id', 'product_qty', 'qty_produced', 'date_finished', 
         'move_raw_ids', 'move_finished_ids'],
        limit=20,
        order='date_finished desc'
    )
    
    print(f"\n📊 Total MOs encontradas: {len(mos)}")
    
    if not mos:
        print("❌ No hay MOs en ese período")
        return
    
    # Analizar cada MO
    for i, mo in enumerate(mos[:5]):  # Solo primeras 5
        print(f"\n\n{'='*80}")
        print(f"MO #{i+1}: {mo['name']}")
        print(f"{'='*80}")
        
        prod = mo.get('product_id')
        prod_name = prod[1] if prod else 'N/A'
        print(f"Producto MO: {prod_name}")
        print(f"Qty producida: {mo.get('qty_produced', 0)}")
        print(f"Fecha: {mo.get('date_finished', 'N/A')}")
        
        # CONSUMOS (move_raw_ids)
        move_raw_ids = mo.get('move_raw_ids', [])
        print(f"\n📥 CONSUMOS ({len(move_raw_ids)} moves):")
        
        if move_raw_ids:
            lines = odoo.search_read(
                'stock.move.line',
                [['move_id', 'in', move_raw_ids]],
                ['product_id', 'lot_id', 'qty_done'],
                limit=20
            )
            
            total_consumo = 0
            for line in lines[:10]:
                prod_info = line.get('product_id')
                prod_name = prod_info[1] if prod_info else 'N/A'
                lot_info = line.get('lot_id')
                lot_name = lot_info[1] if lot_info else 'SIN LOTE'
                qty = line.get('qty_done', 0)
                total_consumo += qty
                
                # Verificar si pasa filtro de fruta
                FRUTAS = ['arándano', 'arandano', 'frambuesa', 'frutilla', 'mora', 'cereza', 'grosella']
                es_fruta = any(f in prod_name.lower() for f in FRUTAS)
                marca = "✅ FRUTA" if es_fruta else "❌ NO ES FRUTA"
                
                print(f"   - {prod_name[:60]}")
                print(f"     Lote: {lot_name} | Qty: {qty:.2f} | {marca}")
            
            print(f"\n   📊 Total consumo (todas las líneas): {total_consumo:.2f} Kg")
        
        # PRODUCCIÓN (move_finished_ids)
        move_finished_ids = mo.get('move_finished_ids', [])
        print(f"\n📤 PRODUCCIÓN ({len(move_finished_ids)} moves):")
        
        if move_finished_ids:
            lines = odoo.search_read(
                'stock.move.line',
                [['move_id', 'in', move_finished_ids]],
                ['product_id', 'lot_id', 'qty_done'],
                limit=20
            )
            
            total_produccion = 0
            for line in lines[:10]:
                prod_info = line.get('product_id')
                prod_name = prod_info[1] if prod_info else 'N/A'
                lot_info = line.get('lot_id')
                lot_name = lot_info[1] if lot_info else 'SIN LOTE'
                qty = line.get('qty_done', 0)
                total_produccion += qty
                
                # Verificar si pasa filtro de fruta
                FRUTAS = ['arándano', 'arandano', 'frambuesa', 'frutilla', 'mora', 'cereza', 'grosella']
                es_fruta = any(f in prod_name.lower() for f in FRUTAS)
                marca = "✅ FRUTA" if es_fruta else "❌ NO ES FRUTA"
                
                print(f"   - {prod_name[:60]}")
                print(f"     Lote: {lot_name} | Qty: {qty:.2f} | {marca}")
            
            print(f"\n   📊 Total producción (todas las líneas): {total_produccion:.2f} Kg")
        else:
            print("   ⚠️ No hay move_finished_ids")
    
    # Resumen
    print("\n\n" + "="*80)
    print("📋 CONCLUSIÓN")
    print("="*80)
    print("""
    Si los productos de PRODUCCIÓN no tienen 'mora', 'frambuesa', etc. en el nombre,
    no pasan el filtro y se muestran como 0 Kg PT.
    
    SOLUCIÓN: Revisar qué nombres tienen los productos PT y ajustar el filtro,
    o cambiar la lógica para NO filtrar la producción por tipo de fruta.
    """)


if __name__ == "__main__":
    main()
