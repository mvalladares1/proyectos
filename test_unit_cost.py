"""
Script para investigar el campo unit_cost en Odoo
Usa las credenciales del archivo .env
"""
import xmlrpc.client
from dotenv import load_dotenv
import os

load_dotenv()

ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USER = os.getenv("ODOO_USER")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

print(f"Conectando a: {ODOO_URL}")
print(f"Base de datos: {ODOO_DB}")
print(f"Usuario: {ODOO_USER}")

# Conexión
common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
print(f"UID: {uid}")

models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

# Buscar una orden específica para probar
of_id = 5035
print(f"\n=== Consultando OF {of_id} ===")

# Obtener move_raw_ids de la OF
of_data = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'mrp.production', 'read', [[of_id]], {'fields': ['name', 'move_raw_ids', 'move_finished_ids']})
print(f"OF: {of_data[0]['name']}")

move_ids = of_data[0].get('move_raw_ids', [])
print(f"Move IDs (componentes): {move_ids[:5]}...")

if move_ids:
    # Buscar stock.move.line para estos moves
    line_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'stock.move.line', 'search', [[['move_id', 'in', move_ids[:3]]]])
    print(f"\nLine IDs encontrados: {line_ids}")
    
    if line_ids:
        # Ver qué campos tiene stock.move.line
        print("\n=== Campos de stock.move.line ===")
        fields = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'stock.move.line', 'fields_get', [], {'attributes': ['string', 'type']})
        price_fields = {k: v for k, v in fields.items() if 'price' in k.lower() or 'cost' in k.lower() or 'unit' in k.lower()}
        for field, info in price_fields.items():
            print(f"  {field}: {info['string']} ({info['type']})")
        
        # Leer datos de la línea
        line_data = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'stock.move.line', 'read', [line_ids[:1]], {'fields': ['product_id', 'qty_done', 'move_id']})
        print(f"\nDatos de línea: {line_data}")
        
        move_id = line_data[0]['move_id'][0] if line_data[0].get('move_id') else None
        
        if move_id:
            # Buscar en stock.valuation.layer
            print(f"\n=== Buscando en stock.valuation.layer para move_id={move_id} ===")
            valuation_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'stock.valuation.layer', 'search', [[['stock_move_id', '=', move_id]]])
            print(f"Valuation IDs: {valuation_ids}")
            
            if valuation_ids:
                val_data = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'stock.valuation.layer', 'read', [valuation_ids], {'fields': ['unit_cost', 'quantity', 'value', 'product_id', 'stock_move_id']})
                print(f"Datos de valoración:")
                for v in val_data:
                    print(f"  - unit_cost: {v.get('unit_cost')}, quantity: {v.get('quantity')}, value: {v.get('value')}")
            else:
                # Probar con stock.move directamente
                print("\n=== Probando campos de stock.move ===")
                move_fields = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'stock.move', 'fields_get', [], {'attributes': ['string', 'type']})
                price_move_fields = {k: v for k, v in move_fields.items() if 'price' in k.lower() or 'cost' in k.lower() or 'value' in k.lower()}
                for field, info in price_move_fields.items():
                    print(f"  {field}: {info['string']} ({info['type']})")
                
                move_data = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'stock.move', 'read', [[move_id]], {'fields': ['price_unit', 'product_id', 'product_qty']})
                print(f"\nDatos de move: {move_data}")

print("\n=== FIN ===")
