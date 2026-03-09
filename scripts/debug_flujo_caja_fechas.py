#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug: Investigar por qué cambian los valores de marzo cuando cambia el rango de fechas
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
import xmlrpc.client
import json

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Autenticar
common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

print("\n" + "="*120)
print("DEBUG: INVESTIGAR CAMBIO DE VALORES EN MARZO SEGÚN RANGO DE FECHAS")
print("="*120)

# Casos a comparar
casos = [
    {
        'nombre': 'CASO 1: 01-02-2026 a 04-07-2026',
        'fecha_inicio': '2026-02-01',
        'fecha_fin': '2026-07-04'
    },
    {
        'nombre': 'CASO 2: 01-03-2026 a 04-07-2026',
        'fecha_inicio': '2026-03-01',
        'fecha_fin': '2026-07-04'
    }
]

# Obtener cuentas de efectivo (las mismas que usa el backend)
print("\n1. OBTENIENDO CUENTAS DE EFECTIVO:")
print("-" * 120)

# Buscar cuentas que empiecen con 110 o 111
domain = ['|', ['code', '=like', '110%'], ['code', '=like', '111%']]

cuentas_efectivo = models.execute_kw(
    DB, uid, PASSWORD,
    'account.account', 'search_read',
    [domain],
    {'fields': ['id', 'code', 'name']}
)

cuentas_efectivo_ids = [c['id'] for c in cuentas_efectivo]
print(f"Encontradas {len(cuentas_efectivo_ids)} cuentas de efectivo")
for c in cuentas_efectivo:
    print(f"  - {c['code']} | {c['name']}")

# Analizar cada caso
resultados_por_caso = {}

for caso in casos:
    print(f"\n{'='*120}")
    print(f"{caso['nombre']}")
    print(f"{'='*120}")
    
    fecha_inicio = caso['fecha_inicio']
    fecha_fin = caso['fecha_fin']
    
    # 2. Obtener movimientos de efectivo
    print(f"\n2. MOVIMIENTOS DE EFECTIVO ({fecha_inicio} a {fecha_fin}):")
    print("-" * 120)
    
    # Buscar todos los account.move.line que afectan cuentas de efectivo en el período
    domain = [
        ['account_id', 'in', cuentas_efectivo_ids],
        ['date', '>=', fecha_inicio],
        ['date', '<=', fecha_fin],
        ['parent_state', '=', 'posted']  # Solo asientos contabilizados
    ]
    
    move_lines = models.execute_kw(
        DB, uid, PASSWORD,
        'account.move.line', 'search_read',
        [domain],
        {'fields': ['id', 'date', 'name', 'ref', 'debit', 'credit', 'balance', 
                   'account_id', 'move_id', 'partner_id', 'journal_id']}
    )
    
    print(f"Total movimientos encontrados: {len(move_lines)}")
    
    # 3. Agrupar por semana/mes de marzo (2026-03-01 a 2026-03-31)
    print(f"\n3. MOVIMIENTOS DE MARZO (2026-03-01 a 2026-03-31):")
    print("-" * 120)
    
    movimientos_marzo = [m for m in move_lines if m['date'] >= '2026-03-01' and m['date'] <= '2026-03-31']
    print(f"Movimientos de marzo: {len(movimientos_marzo)}")
    
    # Agrupar por semana
    semanas_marzo = {}
    for m in movimientos_marzo:
        fecha = datetime.strptime(m['date'], '%Y-%m-%d')
        # Calcular número de semana ISO
        iso_year, iso_week, iso_day = fecha.isocalendar()
        semana_key = f"S{iso_week}"
        
        if semana_key not in semanas_marzo:
            semanas_marzo[semana_key] = {
                'movimientos': [],
                'total_debit': 0,
                'total_credit': 0,
                'neto': 0
            }
        
        semanas_marzo[semana_key]['movimientos'].append(m)
        semanas_marzo[semana_key]['total_debit'] += m['debit']
        semanas_marzo[semana_key]['total_credit'] += m['credit']
        semanas_marzo[semana_key]['neto'] += (m['debit'] - m['credit'])
    
    # Mostrar resumen por semana
    for semana in sorted(semanas_marzo.keys()):
        data = semanas_marzo[semana]
        print(f"\n  {semana}:")
        print(f"    Movimientos: {len(data['movimientos'])}")
        print(f"    Total Débito: ${data['total_debit']:,.0f}")
        print(f"    Total Crédito: ${data['total_credit']:,.0f}")
        print(f"    Neto: ${data['neto']:,.0f}")
    
    # 4. Buscar facturas no pagadas que afectan marzo
    print(f"\n4. FACTURAS NO PAGADAS QUE APARECEN EN MARZO:")
    print("-" * 120)
    
    # Buscar account.move (facturas) que:
    # - Tienen fecha en el período consultado
    # - Son de tipo 'in_invoice' (facturas de proveedor)
    # - Tienen payment_state en ['not_paid', 'partial']
    
    facturas_domain = [
        ['invoice_date', '>=', fecha_inicio],
        ['invoice_date', '<=', fecha_fin],
        ['move_type', '=', 'in_invoice'],
        ['state', '=', 'posted'],
        ['payment_state', 'in', ['not_paid', 'partial']]
    ]
    
    facturas = models.execute_kw(
        DB, uid, PASSWORD,
        'account.move', 'search_read',
        [facturas_domain],
        {'fields': ['id', 'name', 'ref', 'invoice_date', 'partner_id', 'amount_total', 
                   'amount_residual', 'payment_state', 'invoice_partner_display_name']}
    )
    
    print(f"Total facturas no pagadas en período: {len(facturas)}")
    
    # Filtrar solo las de marzo
    facturas_marzo = [f for f in facturas if f['invoice_date'] >= '2026-03-01' and f['invoice_date'] <= '2026-03-31']
    print(f"Facturas no pagadas de marzo: {len(facturas_marzo)}")
    
    # Agrupar por semana
    facturas_por_semana = {}
    for f in facturas_marzo:
        fecha = datetime.strptime(f['invoice_date'], '%Y-%m-%d')
        iso_year, iso_week, iso_day = fecha.isocalendar()
        semana_key = f"S{iso_week}"
        
        if semana_key not in facturas_por_semana:
            facturas_por_semana[semana_key] = []
        
        facturas_por_semana[semana_key].append(f)
    
    for semana in sorted(facturas_por_semana.keys()):
        facturas_sem = facturas_por_semana[semana]
        total_sem = sum(f['amount_residual'] for f in facturas_sem)
        print(f"\n  {semana}:")
        print(f"    Facturas: {len(facturas_sem)}")
        print(f"    Total pendiente: ${total_sem:,.0f}")
        for f in facturas_sem[:5]:  # Mostrar solo las primeras 5
            partner = f.get('invoice_partner_display_name', 'N/A')
            print(f"      - {f['name']}: {partner} - ${f['amount_residual']:,.0f}")
    
    # Guardar resultados
    resultados_por_caso[caso['nombre']] = {
        'total_movimientos': len(move_lines),
        'movimientos_marzo': len(movimientos_marzo),
        'semanas_marzo': semanas_marzo,
        'facturas_marzo': len(facturas_marzo),
        'facturas_por_semana': facturas_por_semana
    }

# 5. COMPARACIÓN
print(f"\n{'='*120}")
print("5. COMPARACIÓN ENTRE CASOS")
print(f"{'='*120}")

caso1 = resultados_por_caso[casos[0]['nombre']]
caso2 = resultados_por_caso[casos[1]['nombre']]

print(f"\n  Total Movimientos:")
print(f"    Caso 1 (Feb-Jul): {caso1['total_movimientos']}")
print(f"    Caso 2 (Mar-Jul): {caso2['total_movimientos']}")

print(f"\n  Movimientos de Marzo:")
print(f"    Caso 1: {caso1['movimientos_marzo']}")
print(f"    Caso 2: {caso2['movimientos_marzo']}")
print(f"    ¿Iguales?: {'✅ SÍ' if caso1['movimientos_marzo'] == caso2['movimientos_marzo'] else '❌ NO - ESTO ES EL PROBLEMA!'}")

print(f"\n  Comparación por Semana de Marzo:")
semanas = set(list(caso1['semanas_marzo'].keys()) + list(caso2['semanas_marzo'].keys()))
for semana in sorted(semanas):
    neto1 = caso1['semanas_marzo'].get(semana, {}).get('neto', 0)
    neto2 = caso2['semanas_marzo'].get(semana, {}).get('neto', 0)
    match = '✅' if abs(neto1 - neto2) < 1 else '❌'
    print(f"    {semana}: ${neto1:,.0f} vs ${neto2:,.0f} {match}")

print(f"\n  Facturas No Pagadas de Marzo:")
print(f"    Caso 1: {caso1['facturas_marzo']}")
print(f"    Caso 2: {caso2['facturas_marzo']}")
print(f"    ¿Iguales?: {'✅ SÍ' if caso1['facturas_marzo'] == caso2['facturas_marzo'] else '❌ NO'}")

# 6. Buscar la discrepancia exacta
print(f"\n{'='*120}")
print("6. BÚSQUEDA DE DISCREPANCIA EN S10-S13")
print(f"{'='*120}")

# Vamos a buscar específicamente qué facturas están apareciendo diferentes
for semana in ['S10', 'S11', 'S12', 'S13']:
    print(f"\n  {semana}:")
    
    fact1 = caso1['facturas_por_semana'].get(semana, [])
    fact2 = caso2['facturas_por_semana'].get(semana, [])
    
    ids1 = set(f['id'] for f in fact1)
    ids2 = set(f['id'] for f in fact2)
    
    solo_caso1 = ids1 - ids2
    solo_caso2 = ids2 - ids1
    comunes = ids1 & ids2
    
    print(f"    Facturas solo en Caso 1: {len(solo_caso1)}")
    print(f"    Facturas solo en Caso 2: {len(solo_caso2)}")
    print(f"    Facturas comunes: {len(comunes)}")
    
    if solo_caso1:
        print(f"    → Solo en Caso 1 (Feb-Jul):")
        for fid in solo_caso1:
            f = next(f for f in fact1 if f['id'] == fid)
            print(f"       {f['name']}: ${f['amount_residual']:,.0f} - Fecha: {f['invoice_date']}")
    
    if solo_caso2:
        print(f"    → Solo en Caso 2 (Mar-Jul):")
        for fid in solo_caso2:
            f = next(f for f in fact2 if f['id'] == fid)
            print(f"       {f['name']}: ${f['amount_residual']:,.0f} - Fecha: {f['invoice_date']}")

print("\n✅ Debug completado")
