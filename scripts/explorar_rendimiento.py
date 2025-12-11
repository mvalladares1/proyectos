"""
Script exploratorio para entender la trazabilidad de lotes en Odoo.
Objetivo: Mapear el flujo Lote MP → MO → Lote PT

Ejecutar desde la raíz del proyecto:
    python scripts/explorar_rendimiento.py --user TU_EMAIL --password TU_API_KEY

O ejecutar sin argumentos para entrada interactiva.
"""
import sys
import os
import argparse
from datetime import datetime, timedelta
from pprint import pprint
from getpass import getpass

# Agregar el directorio padre al path para importar shared
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient


def get_credentials():
    """Obtiene credenciales de argumentos, .env o interactivamente."""
    parser = argparse.ArgumentParser(description='Explorar trazabilidad de rendimiento en Odoo')
    parser.add_argument('--user', '-u', help='Usuario Odoo (email)')
    parser.add_argument('--password', '-p', help='API Key de Odoo')
    args = parser.parse_args()
    
    username = args.user or os.getenv('ODOO_USER')
    password = args.password or os.getenv('ODOO_PASSWORD')
    
    # Si no hay credenciales, preguntar interactivamente
    if not username:
        print("\n📝 Ingresa las credenciales de Odoo:")
        username = input("   Usuario (email): ").strip()
    if not password:
        password = getpass("   API Key: ").strip()
    
    return username, password


def explorar_mo_reciente(odoo: OdooClient):
    """Explora una MO reciente para entender la estructura."""
    print("\n" + "="*80)
    print("1. BUSCANDO MO RECIENTE (estado 'done')")
    print("="*80)
    
    # Buscar una MO terminada reciente
    mos = odoo.search_read(
        'mrp.production',
        [['state', '=', 'done']],
        [
            'name', 'product_id', 'product_qty', 'qty_produced',
            'date_start', 'date_finished', 'state',
            'move_raw_ids', 'move_finished_ids'
        ],
        limit=1,
        order='date_finished desc'
    )
    
    if not mos:
        print("⚠️ No se encontraron MO terminadas")
        return None
    
    mo = mos[0]
    print(f"\n✅ MO encontrada: {mo['name']}")
    print(f"   Producto: {mo['product_id']}")
    print(f"   Cantidad planificada: {mo['product_qty']}")
    print(f"   Cantidad producida: {mo['qty_produced']}")
    print(f"   Fecha inicio: {mo['date_start']}")
    print(f"   Fecha fin: {mo['date_finished']}")
    print(f"   move_raw_ids (consumos): {len(mo.get('move_raw_ids', []))} movimientos")
    print(f"   move_finished_ids (producción): {len(mo.get('move_finished_ids', []))} movimientos")
    
    return mo


def explorar_consumos(odoo: OdooClient, mo: dict):
    """Explora los consumos (MP) de una MO."""
    print("\n" + "="*80)
    print("2. CONSUMOS DE MP (move_raw_ids)")
    print("="*80)
    
    move_raw_ids = mo.get('move_raw_ids', [])
    if not move_raw_ids:
        print("⚠️ No hay move_raw_ids")
        return []
    
    # Obtener stock.move (movimientos)
    moves = odoo.read('stock.move', move_raw_ids, [
        'product_id', 'product_uom_qty', 'state',
        'raw_material_production_id', 'production_id'
    ])
    
    print(f"\n📦 Movimientos de consumo (stock.move):")
    for m in moves[:3]:  # Mostrar solo 3 para no saturar
        print(f"   - {m['product_id']} | qty: {m.get('product_uom_qty', 0)}")
        print(f"     raw_material_production_id: {m.get('raw_material_production_id')}")
        print(f"     production_id: {m.get('production_id')}")
    
    # Obtener stock.move.line para ver lotes
    print("\n📋 Líneas de movimiento (stock.move.line) con LOTES:")
    move_lines = odoo.search_read(
        'stock.move.line',
        [['move_id', 'in', move_raw_ids]],
        [
            'product_id', 'lot_id', 'qty_done', 'date',
            'package_id', 'result_package_id',
            'location_id', 'location_dest_id'
        ],
        limit=5
    )
    
    lotes_consumidos = []
    for ml in move_lines:
        lot_info = ml.get('lot_id')
        lot_name = lot_info[1] if lot_info else "SIN LOTE"
        lot_id = lot_info[0] if lot_info else None
        print(f"   - Producto: {ml['product_id']}")
        print(f"     Lote: {lot_name} (ID: {lot_id})")
        print(f"     Kg consumidos: {ml['qty_done']}")
        print(f"     Fecha: {ml.get('date')}")
        print()
        if lot_id:
            lotes_consumidos.append({'lot_id': lot_id, 'lot_name': lot_name, 'qty': ml['qty_done']})
    
    return lotes_consumidos


def explorar_produccion(odoo: OdooClient, mo: dict):
    """Explora la producción (PT) de una MO."""
    print("\n" + "="*80)
    print("3. PRODUCCIÓN DE PT (move_finished_ids)")
    print("="*80)
    
    move_finished_ids = mo.get('move_finished_ids', [])
    if not move_finished_ids:
        print("⚠️ No hay move_finished_ids")
        return []
    
    # Obtener stock.move
    moves = odoo.read('stock.move', move_finished_ids, [
        'product_id', 'product_uom_qty', 'state'
    ])
    
    print(f"\n📦 Movimientos de producción (stock.move):")
    for m in moves[:3]:
        print(f"   - {m['product_id']} | qty: {m.get('product_uom_qty', 0)}")
    
    # Obtener stock.move.line para ver lotes PT
    print("\n📋 Líneas de producción (stock.move.line) con LOTES PT:")
    move_lines = odoo.search_read(
        'stock.move.line',
        [['move_id', 'in', move_finished_ids]],
        [
            'product_id', 'lot_id', 'qty_done', 'date',
            'package_id', 'result_package_id'
        ],
        limit=5
    )
    
    lotes_producidos = []
    for ml in move_lines:
        lot_info = ml.get('lot_id')
        lot_name = lot_info[1] if lot_info else "SIN LOTE"
        lot_id = lot_info[0] if lot_info else None
        print(f"   - Producto PT: {ml['product_id']}")
        print(f"     Lote PT: {lot_name} (ID: {lot_id})")
        print(f"     Kg producidos: {ml['qty_done']}")
        print()
        if lot_id:
            lotes_producidos.append({'lot_id': lot_id, 'lot_name': lot_name, 'qty': ml['qty_done']})
    
    return lotes_producidos


def explorar_lote_mp(odoo: OdooClient, lot_id: int, lot_name: str):
    """Explora un lote MP específico para encontrar su proveedor y recepción."""
    print("\n" + "="*80)
    print(f"4. TRAZABILIDAD DEL LOTE MP: {lot_name}")
    print("="*80)
    
    # Obtener datos del lote (stock.lot en Odoo antiguo, stock.production.lot en nuevos)
    try:
        lotes = odoo.read('stock.lot', [lot_id], [
            'name', 'product_id', 'create_date', 'company_id'
        ])
    except:
        # Fallback para versiones más nuevas
        lotes = odoo.read('stock.production.lot', [lot_id], [
            'name', 'product_id', 'create_date', 'company_id'
        ])
    
    if lotes:
        lote = lotes[0]
        print(f"\n📋 Datos del lote:")
        print(f"   Nombre: {lote['name']}")
        print(f"   Producto: {lote['product_id']}")
        print(f"   Fecha creación: {lote.get('create_date')}")
    
    # Buscar movimientos de recepción (donde entró este lote)
    print("\n🚚 Buscando recepción del lote (movimiento de entrada)...")
    
    # Buscar move.lines donde se usó este lote
    receipt_lines = odoo.search_read(
        'stock.move.line',
        [
            ['lot_id', '=', lot_id],
            ['location_id.usage', '=', 'supplier']  # Viene de proveedor
        ],
        ['move_id', 'product_id', 'qty_done', 'date', 'location_id', 'location_dest_id'],
        limit=1,
        order='date asc'
    )
    
    if not receipt_lines:
        # Intento alternativo: buscar el primer movimiento de este lote
        print("   No encontrado con location supplier, buscando primero movimiento...")
        receipt_lines = odoo.search_read(
            'stock.move.line',
            [['lot_id', '=', lot_id]],
            ['move_id', 'product_id', 'qty_done', 'date', 'location_id', 'location_dest_id'],
            limit=1,
            order='date asc'
        )
    
    proveedor = None
    if receipt_lines:
        move_id = receipt_lines[0]['move_id'][0] if receipt_lines[0].get('move_id') else None
        print(f"   Movimiento encontrado: ID={move_id}")
        print(f"   Fecha: {receipt_lines[0].get('date')}")
        print(f"   Location origen: {receipt_lines[0].get('location_id')}")
        print(f"   Location destino: {receipt_lines[0].get('location_dest_id')}")
        
        if move_id:
            # Obtener el picking para el proveedor
            moves = odoo.read('stock.move', [move_id], ['picking_id', 'origin'])
            if moves and moves[0].get('picking_id'):
                picking_id = moves[0]['picking_id'][0]
                print(f"\n📦 Picking ID: {picking_id}")
                
                pickings = odoo.read('stock.picking', [picking_id], [
                    'name', 'partner_id', 'scheduled_date', 'origin', 'picking_type_id'
                ])
                
                if pickings:
                    picking = pickings[0]
                    print(f"   Picking: {picking['name']}")
                    print(f"   Proveedor/Partner: {picking.get('partner_id')}")
                    print(f"   Fecha programada: {picking.get('scheduled_date')}")
                    print(f"   Tipo: {picking.get('picking_type_id')}")
                    proveedor = picking.get('partner_id')
    
    return proveedor


def explorar_campos_mo(odoo: OdooClient):
    """Lista los campos disponibles en mrp.production para entender qué datos hay."""
    print("\n" + "="*80)
    print("5. CAMPOS DISPONIBLES EN mrp.production")
    print("="*80)
    
    fields = odoo.execute('mrp.production', 'fields_get', [], {'attributes': ['string', 'type']})
    
    # Filtrar campos relevantes
    campos_utiles = []
    for name, info in fields.items():
        if any(k in name.lower() for k in ['kg', 'hora', 'hh', 'duracion', 'consumo', 'rend', 'merma', 'dotac']):
            campos_utiles.append((name, info.get('string', ''), info.get('type', '')))
    
    if campos_utiles:
        print("\n📋 Campos personalizados relacionados con rendimiento:")
        for name, label, ftype in sorted(campos_utiles):
            print(f"   {name}: {label} ({ftype})")
    
    # Campos de tiempo
    print("\n⏱️ Campos de tiempo:")
    for name, info in fields.items():
        if 'date' in name.lower() or 'time' in name.lower() or 'hora' in name.lower():
            print(f"   {name}: {info.get('string', '')} ({info.get('type', '')})")


def resumen_trazabilidad(lotes_consumidos: list, lotes_producidos: list, proveedor):
    """Muestra un resumen de la trazabilidad encontrada."""
    print("\n" + "="*80)
    print("📊 RESUMEN DE TRAZABILIDAD")
    print("="*80)
    
    total_consumido = sum(l['qty'] for l in lotes_consumidos)
    total_producido = sum(l['qty'] for l in lotes_producidos)
    rendimiento = (total_producido / total_consumido * 100) if total_consumido > 0 else 0
    
    print(f"\n   Lotes MP consumidos: {len(lotes_consumidos)}")
    print(f"   Lotes PT producidos: {len(lotes_producidos)}")
    print(f"   Total Kg consumidos: {total_consumido:,.2f}")
    print(f"   Total Kg producidos: {total_producido:,.2f}")
    print(f"   Rendimiento: {rendimiento:.2f}%")
    print(f"   Merma: {total_consumido - total_producido:,.2f} Kg")
    print(f"   Proveedor: {proveedor}")
    
    print("\n✅ Con esta estructura podemos construir la tabla GOLD")


def main():
    print("="*80)
    print("🔍 SCRIPT EXPLORATORIO - TRAZABILIDAD DE RENDIMIENTO")
    print("="*80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Obtener credenciales interactivamente
    username, password = get_credentials()
    
    # Conectar a Odoo (URL y DB vienen del .env)
    try:
        odoo = OdooClient(username=username, password=password)
        print("\n✅ Conectado a Odoo exitosamente")
    except Exception as e:
        print(f"\n❌ Error conectando a Odoo: {e}")
        return
    
    # 1. Buscar MO reciente
    mo = explorar_mo_reciente(odoo)
    if not mo:
        return
    
    # 2. Explorar consumos
    lotes_consumidos = explorar_consumos(odoo, mo)
    
    # 3. Explorar producción
    lotes_producidos = explorar_produccion(odoo, mo)
    
    # 4. Explorar trazabilidad de un lote MP
    proveedor = None
    if lotes_consumidos:
        primer_lote = lotes_consumidos[0]
        proveedor = explorar_lote_mp(odoo, primer_lote['lot_id'], primer_lote['lot_name'])
    
    # 5. Campos disponibles en MO
    explorar_campos_mo(odoo)
    
    # Resumen
    resumen_trazabilidad(lotes_consumidos, lotes_producidos, proveedor)
    
    print("\n" + "="*80)
    print("FIN DEL SCRIPT EXPLORATORIO")
    print("="*80)


if __name__ == "__main__":
    main()
