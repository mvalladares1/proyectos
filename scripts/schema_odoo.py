"""
Script para extraer el esquema completo de campos de Odoo para el dashboard de rendimiento.
Genera un archivo JSON con todos los campos de los modelos relevantes.

Ejecutar:
    python scripts/schema_odoo.py
"""
import sys
import os
import json
import argparse
from datetime import datetime
from getpass import getpass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient


def get_credentials():
    """Obtiene credenciales de argumentos, .env o interactivamente."""
    parser = argparse.ArgumentParser(description='Extraer esquema de Odoo')
    parser.add_argument('--user', '-u', help='Usuario Odoo (email)')
    parser.add_argument('--password', '-p', help='API Key de Odoo')
    args = parser.parse_args()
    
    username = args.user or os.getenv('ODOO_USER')
    password = args.password or os.getenv('ODOO_PASSWORD')
    
    if not username:
        print("\n📝 Ingresa las credenciales de Odoo:")
        username = input("   Usuario (email): ").strip()
    if not password:
        password = getpass("   API Key: ").strip()
    
    return username, password


def get_model_fields(odoo: OdooClient, model_name: str) -> dict:
    """Obtiene todos los campos de un modelo con su tipo y label."""
    try:
        fields = odoo.execute(model_name, 'fields_get', [], {'attributes': ['string', 'type', 'relation', 'required', 'readonly']})
        return fields
    except Exception as e:
        print(f"   ⚠️ Error al obtener campos de {model_name}: {e}")
        return {}


def print_fields_summary(fields: dict, model_name: str, filter_keywords: list = None):
    """Imprime un resumen de los campos."""
    print(f"\n📋 {model_name} ({len(fields)} campos)")
    print("-" * 60)
    
    # Categorizar campos
    categories = {
        'custom': [],      # x_studio_*
        'relations': [],   # many2one, one2many, many2many
        'numbers': [],     # float, integer
        'dates': [],       # date, datetime
        'text': [],        # char, text
        'other': []
    }
    
    for name, info in fields.items():
        ftype = info.get('type', '')
        label = info.get('string', '')
        relation = info.get('relation', '')
        
        entry = f"{name}: {label} ({ftype})"
        if relation:
            entry += f" → {relation}"
        
        if name.startswith('x_studio') or name.startswith('x_'):
            categories['custom'].append(entry)
        elif ftype in ['many2one', 'one2many', 'many2many']:
            categories['relations'].append(entry)
        elif ftype in ['float', 'integer', 'monetary']:
            categories['numbers'].append(entry)
        elif ftype in ['date', 'datetime']:
            categories['dates'].append(entry)
        elif ftype in ['char', 'text', 'html']:
            categories['text'].append(entry)
        else:
            categories['other'].append(entry)
    
    # Mostrar campos custom primero (los más importantes para el dashboard)
    if categories['custom']:
        print(f"\n🔧 Campos Custom ({len(categories['custom'])}):")
        for f in sorted(categories['custom']):
            print(f"   {f}")
    
    if categories['numbers']:
        print(f"\n🔢 Campos Numéricos ({len(categories['numbers'])}):")
        for f in sorted(categories['numbers'])[:15]:  # Limitar
            print(f"   {f}")
        if len(categories['numbers']) > 15:
            print(f"   ... y {len(categories['numbers'])-15} más")
    
    if categories['dates']:
        print(f"\n📅 Campos de Fecha ({len(categories['dates'])}):")
        for f in sorted(categories['dates']):
            print(f"   {f}")
    
    if categories['relations']:
        print(f"\n🔗 Relaciones ({len(categories['relations'])}):")
        for f in sorted(categories['relations'])[:20]:  # Limitar
            print(f"   {f}")
        if len(categories['relations']) > 20:
            print(f"   ... y {len(categories['relations'])-20} más")


def main():
    print("="*80)
    print("📦 EXTRACCIÓN DE ESQUEMA ODOO - MODELOS DE RENDIMIENTO")
    print("="*80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    username, password = get_credentials()
    
    try:
        odoo = OdooClient(username=username, password=password)
        print("\n✅ Conectado a Odoo exitosamente")
    except Exception as e:
        print(f"\n❌ Error conectando a Odoo: {e}")
        return
    
    # Modelos a explorar
    models = [
        'mrp.production',      # Órdenes de fabricación
        'stock.move',          # Movimientos de stock
        'stock.move.line',     # Líneas de movimiento (con lotes)
        'stock.lot',           # Lotes
        'stock.picking',       # Recepciones/Despachos
        'product.product',     # Productos
    ]
    
    schema = {}
    
    for model in models:
        print(f"\n🔍 Explorando {model}...")
        fields = get_model_fields(odoo, model)
        if fields:
            schema[model] = fields
            print_fields_summary(fields, model)
    
    # Guardar schema completo a JSON
    output_file = os.path.join(os.path.dirname(__file__), 'schema_odoo.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Schema guardado en: {output_file}")
    
    # Resumen final
    print("\n" + "="*80)
    print("📊 RESUMEN DE CAMPOS RELEVANTES PARA RENDIMIENTO")
    print("="*80)
    
    print("""
    MRP.PRODUCTION (Órdenes de Fabricación):
    ├── name, product_id, product_qty, qty_produced
    ├── date_start, date_finished
    ├── move_raw_ids → stock.move (consumos)
    ├── move_finished_ids → stock.move (producción)
    └── x_studio_* (campos custom: dotación, HH, merma, etc.)
    
    STOCK.MOVE (Movimientos):
    ├── product_id, product_uom_qty
    ├── raw_material_production_id → mrp.production (si es consumo)
    └── production_id → mrp.production (si es producción)
    
    STOCK.MOVE.LINE (Líneas con Lotes):
    ├── lot_id → stock.lot
    ├── qty_done
    ├── date
    └── location_id, location_dest_id
    
    STOCK.LOT (Lotes):
    ├── name, product_id, create_date
    └── (para obtener proveedor: buscar primer movimiento del lote → picking → partner_id)
    
    STOCK.PICKING (Recepciones):
    └── partner_id → res.partner (proveedor)
    """)
    
    print("="*80)
    print("FIN DE LA EXTRACCIÓN")
    print("="*80)


if __name__ == "__main__":
    main()
