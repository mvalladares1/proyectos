"""
Script para triggear la automatización de SO Asociada en ODFs.

Este script identifica ODFs que tienen PO Cliente pero no SO Asociada,
y triggea la automatización borrando y reescribiendo el campo PO Cliente.

Uso:
    # Listar ODFs pendientes
    python scripts/trigger_so_asociada.py --list

    # Procesar un ODF específico
    python scripts/trigger_so_asociada.py --odf-id 12345

    # Procesar todos los ODFs pendientes (máximo 10)
    python scripts/trigger_so_asociada.py --all --limit 10

    # Procesar sin límite
    python scripts/trigger_so_asociada.py --all
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
import xmlrpc.client
from datetime import datetime


# Configuración de Odoo
ODOO_URL = "https://riofuturo.server98c6e.oerpondemand.net"
ODOO_DB = "riofuturo-master"
ODOO_USERNAME = os.getenv('ODOO_USERNAME', 'admin')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')


class SimpleOdooClient:
    """Cliente simple de Odoo usando xmlrpc."""
    
    def __init__(self):
        if not ODOO_PASSWORD:
            raise ValueError("ODOO_PASSWORD no está configurado")
        
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        self.uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        self.models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        print(f"✓ Conectado a Odoo como {ODOO_USERNAME} (UID: {self.uid})")


def listar_odfs_pendientes(odoo_client, limit=None):
    """Lista ODFs que tienen PO Cliente pero no SO Asociada."""
    domain = [
        ('x_studio_po_cliente_1', '!=', False),
        ('x_studio_po_cliente_1', '!=', ''),
        '|',
        ('x_studio_po_asociada', '=', False),
        ('x_studio_po_asociada', '=', ''),
        ('state', 'in', ['confirmed', 'progress', 'to_close'])
    ]
    
    fields = [
        'name',
        'product_id',
        'x_studio_po_cliente_1',
        'x_studio_po_asociada',
        'state',
        'date_planned_start'
    ]
    
    odfs = odoo_client.models.execute_kw(
        ODOO_DB, odoo_client.uid, ODOO_PASSWORD,
        'mrp.production',
        'search_read',
        [domain],
        {'fields': fields, 'limit': limit, 'order': 'date_planned_start desc'}
    )
    
    return odfs


def trigger_so_asociada(odoo_client, odf_id, wait_seconds=2.0):
    """Triggea la automatización de SO Asociada para un ODF."""
    import time
    
    # 1. Leer valor actual
    odf = odoo_client.models.execute_kw(
        ODOO_DB, odoo_client.uid, ODOO_PASSWORD,
        'mrp.production',
        'read',
        [[odf_id]],
        {'fields': ['name', 'x_studio_po_cliente_1', 'x_studio_po_asociada']}
    )
    
    if not odf:
        print(f"  ✗ ODF {odf_id} no encontrado")
        return False
    
    odf = odf[0]
    po_cliente = odf.get('x_studio_po_cliente_1')
    
    if not po_cliente:
        print(f"  ✗ ODF {odf.get('name')} no tiene PO Cliente")
        return False
    
    print(f"\n  Procesando ODF {odf.get('name')}")
    print(f"    PO Cliente: {po_cliente}")
    
    # 2. Borrar el campo
    odoo_client.models.execute_kw(
        ODOO_DB, odoo_client.uid, ODOO_PASSWORD,
        'mrp.production',
        'write',
        [[odf_id], {'x_studio_po_cliente_1': False}]
    )
    print(f"    → Campo PO Cliente borrado")
    time.sleep(wait_seconds)
    
    # 3. Reescribir el campo
    odoo_client.models.execute_kw(
        ODOO_DB, odoo_client.uid, ODOO_PASSWORD,
        'mrp.production',
        'write',
        [[odf_id], {'x_studio_po_cliente_1': po_cliente}]
    )
    print(f"    → Campo PO Cliente reescrito")
    time.sleep(wait_seconds)
    
    # 4. Verificar resultado
    odf_updated = odoo_client.models.execute_kw(
        ODOO_DB, odoo_client.uid, ODOO_PASSWORD,
        'mrp.production',
        'read',
        [[odf_id]],
        {'fields': ['x_studio_po_asociada']}
    )[0]
    
    so_asociada = odf_updated.get('x_studio_po_asociada')
    
    if so_asociada:
        print(f"    ✓ SO Asociada cargada: {so_asociada}")
        return True
    else:
        print(f"    ✗ SO Asociada no se cargó (posiblemente no existe SO con ese origen)")
        return False


def main():
    parser = argparse.ArgumentParser(description='Triggear automatización de SO Asociada')
    parser.add_argument('--list', action='store_true', help='Listar ODFs pendientes')
    parser.add_argument('--odf-id', type=int, help='ID del ODF a procesar')
    parser.add_argument('--odf-name', type=str, help='Nombre del ODF a procesar (ej: WH/Transf/00821)')
    parser.add_argument('--all', action='store_true', help='Procesar todos los ODFs pendientes')
    parser.add_argument('--limit', type=int, help='Límite de ODFs a procesar')
    parser.add_argument('--wait', type=float, default=2.0, help='Segundos a esperar entre operaciones')
    
    args = parser.parse_args()
    
    try:
        # Conectar a Odoo
        odoo = SimpleOdooClient()
        
        # Modo: listar ODFs pendientes
        if args.list:
            print("\n📋 ODFs pendientes de cargar SO Asociada:\n")
            odfs = listar_odfs_pendientes(odoo, args.limit)
            
            if not odfs:
                print("  No hay ODFs pendientes")
                return
            
            for odf in odfs:
                print(f"  • [{odf['id']}] {odf['name']} - PO Cliente: {odf['x_studio_po_cliente_1']}")
                print(f"    Estado: {odf['state']} - Fecha: {odf['date_planned_start']}")
            
            print(f"\n  Total: {len(odfs)} ODFs")
            return
        
        # Modo: procesar ODF por nombre
        if args.odf_name:
            print(f"\n🔄 Buscando ODF {args.odf_name}...\n")
            
            # Buscar ODF por nombre
            odfs = odoo.models.execute_kw(
                ODOO_DB, odoo.uid, ODOO_PASSWORD,
                'mrp.production',
                'search_read',
                [[('name', '=', args.odf_name)]],
                {'fields': ['id', 'name'], 'limit': 1}
            )
            
            if not odfs:
                print(f"  ✗ ODF {args.odf_name} no encontrado")
                return
            
            odf_id = odfs[0]['id']
            print(f"  ✓ ODF encontrado con ID: {odf_id}\n")
            
            success = trigger_so_asociada(odoo, odf_id, args.wait)
            
            if success:
                print(f"\n✓ ODF {args.odf_name} procesado exitosamente")
            else:
                print(f"\n✗ Error procesando ODF {args.odf_name}")
            
            return
        
        # Modo: procesar ODF específico
        if args.odf_id:
            print(f"\n🔄 Procesando ODF {args.odf_id}...\n")
            success = trigger_so_asociada(odoo, args.odf_id, args.wait)
            
            if success:
                print(f"\n✓ ODF {args.odf_id} procesado exitosamente")
            else:
                print(f"\n✗ Error procesando ODF {args.odf_id}")
            
            return
        
        # Modo: procesar todos los ODFs pendientes
        if args.all:
            print(f"\n🔄 Procesando ODFs pendientes...\n")
            odfs = listar_odfs_pendientes(odoo, args.limit)
            
            if not odfs:
                print("  No hay ODFs pendientes")
                return
            
            print(f"  Se procesarán {len(odfs)} ODFs\n")
            
            exitosos = 0
            fallidos = 0
            
            for odf in odfs:
                success = trigger_so_asociada(odoo, odf['id'], args.wait)
                
                if success:
                    exitosos += 1
                else:
                    fallidos += 1
            
            print(f"\n{'='*60}")
            print(f"  RESUMEN:")
            print(f"  Total: {len(odfs)} ODFs")
            print(f"  Exitosos: {exitosos}")
            print(f"  Fallidos: {fallidos}")
            print(f"{'='*60}\n")
            
            return
        
        # Si no se especificó ninguna opción
        parser.print_help()
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
