"""
Script temporal para explorar campos de quality.check en Odoo
Busca campos relacionados con porcentajes IQF/Block/Otros
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.odoo_client import OdooClient
from dotenv import load_dotenv

load_dotenv()

def explore_quality_check_fields():
    client = OdooClient()
    
    # Obtener campos del modelo quality.check
    print("=== Campos de quality.check ===\n")
    
    fields = client.execute('quality.check', 'fields_get', [], {'attributes': ['string', 'type']})
    
    # Filtrar campos x_studio (personalizados) que contengan palabras clave
    keywords = ['iqf', 'block', 'total', 'porcentaje', 'pct', 'merma', 'otro', 'descarte']
    
    print("Campos personalizados relevantes:")
    print("-" * 60)
    
    for field_name, field_info in sorted(fields.items()):
        if field_name.startswith('x_studio'):
            label = field_info.get('string', '')
            field_type = field_info.get('type', '')
            
            # Mostrar todos los campos x_studio que parezcan porcentajes
            lower_name = field_name.lower()
            lower_label = label.lower() if label else ''
            
            if any(kw in lower_name or kw in lower_label for kw in keywords):
                print(f"  {field_name}")
                print(f"    Label: {label}")
                print(f"    Type: {field_type}")
                print()
    
    # También obtener un registro de ejemplo para ver valores
    print("\n=== Ejemplo de datos de un quality.check ===\n")
    
    checks = client.search_read(
        'quality.check',
        [],
        ['x_studio_tipo_de_fruta', 'x_studio_total_iqf_', 'x_studio_total_block_'],
        limit=5
    )
    
    for c in checks:
        tipo = c.get('x_studio_tipo_de_fruta', 'N/A')
        iqf = c.get('x_studio_total_iqf_', 0) or 0
        block = c.get('x_studio_total_block_', 0) or 0
        suma = iqf + block
        print(f"Tipo: {tipo}")
        print(f"  IQF: {iqf}%, Block: {block}%, Suma: {suma}%")
        print(f"  Faltante: {100 - suma:.2f}%")
        print()


if __name__ == "__main__":
    explore_quality_check_fields()
