"""
Script para analizar el comportamiento de la automatización de SO Asociada.

Este script busca ODFs que SÍ tienen SO Asociada para entender el patrón.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import xmlrpc.client


# Configuración de Odoo
ODOO_URL = "https://riofuturo.server98c6e.oerpondemand.net"
ODOO_DB = "riofuturo-master"
ODOO_USERNAME = os.getenv('ODOO_USERNAME', 'mvalladares@riofuturo.cl')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')


def main():
    if not ODOO_PASSWORD:
        print("Error: ODOO_PASSWORD no está configurado")
        return
    
    # Conectar a Odoo
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    
    print(f"✓ Conectado a Odoo como {ODOO_USERNAME} (UID: {uid})\n")
    
    # Buscar ODFs que SÍ tienen SO Asociada
    print("📋 ODFs con SO Asociada:\n")
    
    domain = [
        ('x_studio_po_asociada', '!=', False),
        ('x_studio_po_asociada', '!=', ''),
        ('state', 'in', ['confirmed', 'progress', 'to_close', 'done'])
    ]
    
    fields = [
        'name',
        'product_id',
        'x_studio_po_cliente_1',
        'x_studio_po_asociada',
        'state',
        'date_planned_start'
    ]
    
    odfs = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'mrp.production',
        'search_read',
        [domain],
        {'fields': fields, 'limit': 10, 'order': 'date_planned_start desc'}
    )
    
    if not odfs:
        print("  No se encontraron ODFs con SO Asociada")
        return
    
    for odf in odfs:
        print(f"\n  • [{odf['id']}] {odf['name']}")
        print(f"    PO Cliente: {odf.get('x_studio_po_cliente_1', 'N/A')}")
        print(f"    SO Asociada: {odf.get('x_studio_po_asociada', 'N/A')}")
        print(f"    Estado: {odf['state']}")
        
        # Buscar si existe SO con ese origin
        po_cliente = odf.get('x_studio_po_cliente_1')
        if po_cliente:
            sos = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'sale.order',
                'search_read',
                [[('origin', '=', po_cliente)]],
                {'fields': ['name', 'origin'], 'limit': 5}
            )
            
            if sos:
                print(f"    ✓ SOs encontradas con origin={po_cliente}:")
                for so in sos:
                    print(f"      - {so['name']}")
            else:
                print(f"    ✗ No hay SOs con origin={po_cliente}")
    
    print(f"\n  Total: {len(odfs)} ODFs")
    
    # Ahora buscar ODFs sin SO Asociada pero con PO Cliente
    print("\n\n📋 ODFs sin SO Asociada pero con PO Cliente:\n")
    
    domain = [
        ('x_studio_po_cliente_1', '!=', False),
        ('x_studio_po_cliente_1', '!=', ''),
        '|',
        ('x_studio_po_asociada', '=', False),
        ('x_studio_po_asociada', '=', ''),
        ('state', 'in', ['confirmed', 'progress', 'to_close'])
    ]
    
    odfs_sin = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'mrp.production',
        'search_read',
        [domain],
        {'fields': fields, 'limit': 5, 'order': 'date_planned_start desc'}
    )
    
    for odf in odfs_sin:
        print(f"\n  • [{odf['id']}] {odf['name']}")
        print(f"    PO Cliente: {odf.get('x_studio_po_cliente_1', 'N/A')}")
        print(f"    Estado: {odf['state']}")
        
        # Buscar si existe SO con ese origin
        po_cliente = odf.get('x_studio_po_cliente_1')
        if po_cliente:
            sos = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'sale.order',
                'search_read',
                [[('origin', '=', po_cliente)]],
                {'fields': ['name', 'origin'], 'limit': 5}
            )
            
            if sos:
                print(f"    ✓ SOs encontradas con origin={po_cliente}:")
                for so in sos:
                    print(f"      - {so['name']}")
            else:
                print(f"    ✗ No hay SOs con origin={po_cliente}")
    
    print(f"\n  Total: {len(odfs_sin)} ODFs sin SO Asociada")


if __name__ == "__main__":
    main()
