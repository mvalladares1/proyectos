"""
Script de debug para analizar etiquetas de Flujo de Caja.
Analiza la cuenta 82010102 (INTERESES POR LEASING) en enero 2026.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.services.flujo_caja_service import FlujoCajaService
from shared.odoo_client import OdooClient
import json
from datetime import datetime

# Credenciales (ajustar según necesidad)
USERNAME = input("Usuario Odoo: ") if len(sys.argv) < 2 else sys.argv[1]
PASSWORD = input("Password Odoo: ") if len(sys.argv) < 3 else sys.argv[2]

def debug_cuenta_82010102_enero():
    """Debug de cuenta 82010102 en enero 2026."""
    print("="*80)
    print("DEBUG: Cuenta 82010102 - INTERESES POR LEASING - Enero 2026")
    print("="*80)
    
    service = FlujoCajaService(username=USERNAME, password=PASSWORD)
    odoo = service.odoo
    
    # 1. Obtener cuentas de efectivo
    cuentas_efectivo_ids = service._get_cuentas_efectivo()
    print(f"\n1. Cuentas de efectivo encontradas: {len(cuentas_efectivo_ids)} cuentas")
    print(f"   IDs: {cuentas_efectivo_ids[:5]}...")
    
    # 2. Buscar la cuenta 82010102
    cuenta_target = odoo.search_read(
        'account.account',
        [['code', '=', '82010102']],
        ['id', 'code', 'name']
    )
    
    if not cuenta_target:
        print("\n❌ ERROR: No se encontró la cuenta 82010102")
        return
    
    cuenta = cuenta_target[0]
    print(f"\n2. Cuenta objetivo:")
    print(f"   ID: {cuenta['id']}")
    print(f"   Código: {cuenta['code']}")
    print(f"   Nombre: {cuenta['name']}")
    
    # 3. Buscar movimientos de efectivo en enero 2026
    fecha_inicio = "2026-01-01"
    fecha_fin = "2026-01-31"
    
    movimientos_efectivo = odoo.search_read(
        'account.move.line',
        [
            ['account_id', 'in', cuentas_efectivo_ids],
            ['parent_state', '=', 'posted'],
            ['date', '>=', fecha_inicio],
            ['date', '<=', fecha_fin]
        ],
        ['move_id'],
        limit=10000
    )
    
    asientos_ids = list(set(
        m['move_id'][0] if isinstance(m.get('move_id'), (list, tuple)) else m.get('move_id')
        for m in movimientos_efectivo if m.get('move_id')
    ))
    
    print(f"\n3. Movimientos de efectivo en enero 2026:")
    print(f"   Total asientos: {len(asientos_ids)}")
    
    # 4. Buscar contrapartidas de la cuenta 82010102
    contrapartidas = odoo.search_read(
        'account.move.line',
        [
            ['move_id', 'in', asientos_ids],
            ['account_id', '=', cuenta['id']]
        ],
        ['id', 'move_id', 'name', 'debit', 'credit', 'balance', 'date'],
        limit=1000
    )
    
    print(f"\n4. Líneas de contrapartida para cuenta 82010102:")
    print(f"   Total líneas: {len(contrapartidas)}")
    
    if contrapartidas:
        print("\n   Detalle de líneas:")
        for i, linea in enumerate(contrapartidas[:20], 1):
            print(f"\n   Línea {i}:")
            print(f"      Move ID: {linea.get('move_id')}")
            print(f"      Fecha: {linea.get('date')}")
            print(f"      Name/Etiqueta: {linea.get('name')}")
            print(f"      Débito: {linea.get('debit'):,.2f}")
            print(f"      Crédito: {linea.get('credit'):,.2f}")
            print(f"      Balance: {linea.get('balance'):,.2f}")
    
    # 5. Agrupar por etiqueta (name) usando read_group
    print("\n5. Agrupación por etiqueta (read_group):")
    
    try:
        grupos = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'account.move.line', 'read_group',
            [[
                ['move_id', 'in', asientos_ids],
                ['account_id', '=', cuenta['id']]
            ]],
            {
                'fields': ['balance', 'name'],
                'groupby': ['name'],
                'lazy': False
            }
        )
        
        print(f"   Total grupos (etiquetas únicas): {len(grupos)}")
        for i, grupo in enumerate(grupos, 1):
            etiqueta = grupo.get('name', '')
            balance = grupo.get('balance', 0)
            count = grupo.get('name_count', 0)
            print(f"\n   Grupo {i}:")
            print(f"      Etiqueta: {etiqueta}")
            print(f"      Balance total: {balance:,.2f}")
            print(f"      Cantidad líneas: {count}")
    
    except Exception as e:
        print(f"   ❌ Error en read_group: {e}")
    
    # 6. Agrupar por etiqueta Y mes
    print("\n6. Agrupación por etiqueta Y mes (date:month):")
    
    try:
        grupos_mes = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'account.move.line', 'read_group',
            [[
                ['move_id', 'in', asientos_ids],
                ['account_id', '=', cuenta['id']]
            ]],
            {
                'fields': ['balance', 'name', 'date'],
                'groupby': ['name', 'date:month'],
                'lazy': False
            }
        )
        
        print(f"   Total grupos (etiqueta + mes): {len(grupos_mes)}")
        for i, grupo in enumerate(grupos_mes, 1):
            etiqueta = grupo.get('name', '')
            balance = grupo.get('balance', 0)
            mes = grupo.get('date:month', '')
            count = grupo.get('name_count', 0)
            print(f"\n   Grupo {i}:")
            print(f"      Etiqueta: {etiqueta}")
            print(f"      Mes: {mes}")
            print(f"      Balance: {balance:,.2f}")
            print(f"      Cantidad: {count}")
    
    except Exception as e:
        print(f"   ❌ Error en read_group con mes: {e}")
    
    # 7. Verificar duplicados en etiquetas
    print("\n7. Análisis de posibles duplicados:")
    etiquetas_vistas = {}
    for linea in contrapartidas:
        etiqueta = linea.get('name', '').strip()
        if etiqueta:
            if etiqueta not in etiquetas_vistas:
                etiquetas_vistas[etiqueta] = []
            etiquetas_vistas[etiqueta].append({
                'move_id': linea.get('move_id'),
                'balance': linea.get('balance'),
                'date': linea.get('date')
            })
    
    print(f"   Etiquetas únicas encontradas: {len(etiquetas_vistas)}")
    for etiqueta, lineas in sorted(etiquetas_vistas.items()):
        total_balance = sum(l['balance'] for l in lineas)
        print(f"\n   '{etiqueta}':")
        print(f"      Apariciones: {len(lineas)}")
        print(f"      Balance total: {total_balance:,.2f}")
        if len(lineas) <= 3:
            for l in lineas:
                print(f"         - Move {l['move_id']}: {l['balance']:,.2f} ({l['date']})")
    
    print("\n" + "="*80)
    print("FIN DEBUG")
    print("="*80)

if __name__ == "__main__":
    debug_cuenta_82010102_enero()
