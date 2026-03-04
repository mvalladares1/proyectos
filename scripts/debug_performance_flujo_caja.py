#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug: Analizar performance del flujo de caja
Medir cuántos registros se están procesando y dónde está el cuello de botella
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import xmlrpc.client
import time
from datetime import datetime

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Autenticar
common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

print("\n" + "="*120)
print("DEBUG: ANÁLISIS DE PERFORMANCE - FLUJO DE CAJA")
print("="*120)

# Casos a probar
casos = [
    {
        'nombre': 'CASO 1: Rango corto (Feb-Mar 2026)',
        'fecha_inicio': '2026-02-01',
        'fecha_fin': '2026-03-04'
    },
    {
        'nombre': 'CASO 2: Rango medio (Ene-Jul 2026)',
        'fecha_inicio': '2026-01-01',
        'fecha_fin': '2026-07-04'
    },
    {
        'nombre': 'CASO 3: Rango largo (2025 completo + 2026)',
        'fecha_inicio': '2025-01-01',
        'fecha_fin': '2026-07-04'
    }
]

for caso in casos:
    print(f"\n{'='*120}")
    print(f"{caso['nombre']}")
    print(f"{'='*120}")
    
    fecha_inicio = caso['fecha_inicio']
    fecha_fin = caso['fecha_fin']
    
    # 1. Facturas de proveedor (1.2.1)
    print(f"\n1. FACTURAS DE PROVEEDOR (journal_id=2):")
    print("-" * 120)
    
    start = time.time()
    
    # Con invoice_date (NUEVO - como está ahora en producción)
    facturas_invoice_date = models.execute_kw(
        DB, uid, PASSWORD,
        'account.move', 'search_read',
        [[
            ['move_type', 'in', ['in_invoice', 'in_refund']],
            ['journal_id', '=', 2],
            ['invoice_date', '>=', fecha_inicio],
            ['invoice_date', '<=', fecha_fin],
            ['state', '=', 'posted'],
            ['payment_state', '!=', 'reversed']
        ]],
        {'fields': ['id', 'name', 'invoice_date'], 'limit': 10000}
    )
    
    tiempo_invoice_date = time.time() - start
    
    print(f"  Con invoice_date: {len(facturas_invoice_date)} facturas en {tiempo_invoice_date:.2f}s")
    
    # Con date (ANTIGUO - antes del cambio)
    start = time.time()
    facturas_date = models.execute_kw(
        DB, uid, PASSWORD,
        'account.move', 'search_read',
        [[
            ['move_type', 'in', ['in_invoice', 'in_refund']],
            ['journal_id', '=', 2],
            ['date', '>=', fecha_inicio],
            ['date', '<=', fecha_fin],
            ['state', '=', 'posted'],
            ['payment_state', '!=', 'reversed']
        ]],
        {'fields': ['id', 'name', 'date'], 'limit': 10000}
    )
    
    tiempo_date = time.time() - start
    
    print(f"  Con date:         {len(facturas_date)} facturas en {tiempo_date:.2f}s")
    print(f"  Diferencia:       {len(facturas_invoice_date) - len(facturas_date)} facturas más con invoice_date")
    print(f"  Tiempo extra:     +{(tiempo_invoice_date - tiempo_date):.2f}s")
    
    # 2. Líneas de facturas (account.move.line)
    if len(facturas_invoice_date) > 0:
        print(f"\n2. LÍNEAS DE FACTURAS:")
        print("-" * 120)
        
        factura_ids = [f['id'] for f in facturas_invoice_date[:100]]  # Solo las primeras 100 para test
        
        start = time.time()
        lineas = models.execute_kw(
            DB, uid, PASSWORD,
            'account.move.line', 'search_read',
            [[['move_id', 'in', factura_ids]]],
            {'fields': ['id', 'move_id', 'matching_number', 'date', 'debit', 'credit'], 'limit': 100000}
        )
        tiempo_lineas = time.time() - start
        
        print(f"  Para {len(factura_ids)} facturas: {len(lineas)} líneas en {tiempo_lineas:.2f}s")
        print(f"  Promedio: {len(lineas)/len(factura_ids):.1f} líneas por factura")
    
    # 3. Facturas de cliente (1.1.1)
    print(f"\n3. FACTURAS DE CLIENTE:")
    print("-" * 120)
    
    start = time.time()
    facturas_cliente = models.execute_kw(
        DB, uid, PASSWORD,
        'account.move', 'search_read',
        [[
            ['move_type', '=', 'out_invoice'],
            ['state', '=', 'posted'],
            ['invoice_date', '>=', fecha_inicio],
            ['invoice_date', '<=', fecha_fin],
            ['payment_state', '!=', 'reversed']
        ]],
        {'fields': ['id', 'name', 'invoice_date'], 'limit': 10000}
    )
    tiempo_cliente = time.time() - start
    
    print(f"  Facturas de cliente: {len(facturas_cliente)} en {tiempo_cliente:.2f}s")
    
    # 4. Movimientos de efectivo
    print(f"\n4. MOVIMIENTOS DE EFECTIVO:")
    print("-" * 120)
    
    # Obtener cuentas de efectivo
    domain = ['|', ['code', '=like', '110%'], ['code', '=like', '111%']]
    cuentas_efectivo = models.execute_kw(
        DB, uid, PASSWORD,
        'account.account', 'search_read',
        [domain],
        {'fields': ['id', 'code'], 'limit': 200}
    )
    cuentas_efectivo_ids = [c['id'] for c in cuentas_efectivo]
    
    start = time.time()
    movimientos = models.execute_kw(
        DB, uid, PASSWORD,
        'account.move.line', 'search_read',
        [[
            ['account_id', 'in', cuentas_efectivo_ids],
            ['date', '>=', fecha_inicio],
            ['date', '<=', fecha_fin],
            ['parent_state', '=', 'posted']
        ]],
        {'fields': ['id', 'date', 'debit', 'credit'], 'limit': 100000}
    )
    tiempo_movimientos = time.time() - start
    
    print(f"  Movimientos de efectivo: {len(movimientos)} en {tiempo_movimientos:.2f}s")
    
    # RESUMEN
    print(f"\n{'='*120}")
    print(f"RESUMEN DE TIEMPOS:")
    print(f"{'='*120}")
    total = tiempo_invoice_date + tiempo_cliente + tiempo_movimientos
    print(f"  Facturas proveedor: {tiempo_invoice_date:.2f}s ({len(facturas_invoice_date)} registros)")
    print(f"  Facturas cliente:   {tiempo_cliente:.2f}s ({len(facturas_cliente)} registros)")
    print(f"  Movimientos efectivo: {tiempo_movimientos:.2f}s ({len(movimientos)} registros)")
    print(f"  TOTAL ESTIMADO:     {total:.2f}s")
    print(f"\n  ⚠️ Esto es SOLO el tiempo de queries a Odoo, sin procesamiento Python")

print("\n✅ Debug completado")
