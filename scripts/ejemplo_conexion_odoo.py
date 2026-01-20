"""
Script de ejemplo para conectarse a Odoo desde scripts independientes.

Uso:
    python scripts/ejemplo_conexion_odoo.py

Este script muestra cómo:
1. Conectarse a Odoo usando las credenciales
2. Hacer consultas básicas
3. Procesar resultados
"""

import sys
import os

# Agregar el directorio raíz al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

# Credenciales (reemplazar con las tuyas)
USERNAME = "tu_usuario@riofuturo.cl"
PASSWORD = "tu_api_key_aqui"

def main():
    """Ejemplo de conexión y consulta a Odoo."""
    
    # Conectar a Odoo
    print("Conectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("✓ Conectado exitosamente\n")
    
    # Ejemplo 1: Buscar productos
    print("=" * 80)
    print("EJEMPLO 1: Buscar productos")
    print("=" * 80)
    
    productos = odoo.search_read(
        'product.product',
        [['name', 'ilike', 'frambuesa']],  # Dominio de búsqueda
        ['id', 'name', 'default_code'],     # Campos a obtener
        limit=5
    )
    
    print(f"\nEncontrados {len(productos)} productos:\n")
    for prod in productos:
        print(f"  ID: {prod['id']:<8} Código: {prod.get('default_code', 'N/A'):<15} Nombre: {prod['name'][:50]}")
    
    # Ejemplo 2: Consultar facturas
    print("\n" + "=" * 80)
    print("EJEMPLO 2: Facturas de enero 2026")
    print("=" * 80)
    
    facturas = odoo.search_read(
        'account.move',
        [
            ['move_type', '=', 'out_invoice'],
            ['state', '=', 'posted'],
            ['date', '>=', '2026-01-01'],
            ['date', '<=', '2026-01-31']
        ],
        ['name', 'partner_id', 'amount_total', 'date'],
        limit=5
    )
    
    print(f"\nEncontradas {len(facturas)} facturas:\n")
    for fac in facturas:
        partner = fac.get('partner_id', [None, 'N/A'])
        partner_name = partner[1] if isinstance(partner, list) else str(partner)
        print(f"  {fac['name']:<15} {fac['date']:<12} {partner_name[:30]:<30} ${fac['amount_total']:>15,.0f}")
    
    # Ejemplo 3: Líneas de factura con productos
    print("\n" + "=" * 80)
    print("EJEMPLO 3: Líneas de factura con filtros avanzados")
    print("=" * 80)
    
    lineas = odoo.search_read(
        'account.move.line',
        [
            ['move_id.move_type', '=', 'in_invoice'],  # Filtro por campo relacionado
            ['move_id.state', '=', 'posted'],
            ['product_id', '!=', False],
            ['date', '>=', '2026-01-01'],
            ['date', '<=', '2026-01-31'],
            ['quantity', '>', 0],
            ['debit', '>', 0],
            ['account_id.code', '=like', '21%']  # Cuenta de proveedores
        ],
        ['product_id', 'quantity', 'debit', 'move_id'],
        limit=5
    )
    
    print(f"\nEncontradas {len(lineas)} líneas:\n")
    for linea in lineas:
        prod = linea.get('product_id', [None, 'N/A'])
        prod_name = prod[1][:40] if isinstance(prod, list) else str(prod)
        factura = linea.get('move_id', [None, 'N/A'])
        factura_name = factura[1] if isinstance(factura, list) else str(factura)
        
        print(f"  {factura_name:<20} {prod_name:<40} {linea['quantity']:>10,.2f} kg  ${linea['debit']:>12,.0f}")
    
    print("\n" + "=" * 80)
    print("✓ Ejemplos completados")
    print("=" * 80)

if __name__ == '__main__':
    main()
