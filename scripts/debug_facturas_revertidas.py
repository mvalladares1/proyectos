"""
Script para investigar cómo identificar facturas revertidas en Odoo
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient
from datetime import datetime

# Credenciales
ODOO_USER = input("Usuario Odoo: ")
ODOO_PASSWORD = input("API Key: ")

odoo = OdooClient(username=ODOO_USER, password=ODOO_PASSWORD)

print("\n" + "="*100)
print("INVESTIGACIÓN: CAMPOS DISPONIBLES EN FACTURAS")
print("="*100)

# Buscar una factura de compra reciente
facturas_compra = odoo.search_read(
    'account.move',
    [
        ['move_type', '=', 'in_invoice'],
        ['state', '=', 'posted'],
        ['journal_id.name', '=', 'Facturas de Proveedores'],
        ['date', '>=', '2024-01-01']
    ],
    ['name', 'date', 'amount_total', 'state', 'payment_state'],
    limit=5
)

print(f"\n✅ Facturas de compra encontradas: {len(facturas_compra)}")
if facturas_compra:
    factura_id = facturas_compra[0]['id']
    print(f"Analizando factura: {facturas_compra[0]['name']} (ID: {factura_id})")
    
    # Obtener campos específicos relevantes de esta factura
    campos_a_buscar = [
        'name', 'date', 'state', 'payment_state', 'amount_total',
        'ref', 'invoice_origin'
    ]
    
    factura_completa = odoo.search_read(
        'account.move',
        [['id', '=', factura_id]],
        campos_a_buscar
    )
    
    if factura_completa:
        print("\n📋 Campos relacionados con REVERSIÓN/NC encontrados:")
        campos_relevantes = {}
        
        for key, value in factura_completa[0].items():
            if any(keyword in key.lower() for keyword in ['revers', 'credit', 'refund', 'cancel', 'void']):
                campos_relevantes[key] = value
                print(f"  • {key}: {value}")
        
        if not campos_relevantes:
            print("  ⚠️  No se encontraron campos obvios de reversión")
        
        print("\n📋 Campos de ESTADO:")
        for key in ['state', 'payment_state', 'move_type']:
            if key in factura_completa[0]:
                print(f"  • {key}: {factura_completa[0][key]}")

print("\n" + "="*100)
print("BUSCANDO NOTAS DE CRÉDITO ESPECÍFICAMENTE")
print("="*100)

# Buscar notas de crédito (in_refund)
notas_credito = odoo.search_read(
    'account.move',
    [
        ['move_type', '=', 'in_refund'],
        ['state', '=', 'posted'],
        ['date', '>=', '2024-01-01']
    ],
    ['name', 'date', 'amount_total', 'ref'],
    limit=10
)

print(f"\n✅ Notas de crédito (in_refund) encontradas: {len(notas_credito)}")

if notas_credito:
    nc_id = notas_credito[0]['id']
    print(f"Analizando NC: {notas_credito[0]['name']} (ID: {nc_id})")
    
    # Obtener campos específicos de la NC
    campos_nc = [
        'name', 'date', 'state', 'payment_state', 'amount_total',
        'ref', 'invoice_origin'
    ]
    
    nc_completa = odoo.search_read(
        'account.move',
        [['id', '=', nc_id]],
        campos_nc
    )
    
    if nc_completa:
        print("\n📋 Campos de RELACIÓN con factura original:")
        for key, value in nc_completa[0].items():
            if any(keyword in key.lower() for keyword in ['revers', 'origin', 'ref', 'invoice']):
                print(f"  • {key}: {value}")

print("\n" + "="*100)
print("ESTRATEGIA RECOMENDADA")
print("="*100)

print("""
Basado en los campos encontrados:

Opción 1: Si existe 'reversed_entry_id' o 'reversal_move_id':
   - Filtrar: ['reversed_entry_id', '=', False]
   
Opción 2: Si existe 'reversal_entry_ids':
   - Usar domain: "['reversal_entry_ids', '=', []]" (sin reversiones)
   
Opción 3: Método alternativo - Excluir NC:
   - Para compras: Solo move_type='in_invoice' (NO in_refund)
   - Para ventas: Solo move_type='out_invoice' (NO out_refund)
   - Y verificar que no tengan NC asociadas

Opción 4: Por payment_state:
   - Si payment_state existe: ['payment_state', '!=', 'reversed']
""")

print("\n" + "="*100)
print("CONTEO COMPARATIVO")
print("="*100)

# Contar con y sin filtro
domain_base = [
    ['move_id.move_type', '=', 'in_invoice'],
    ['move_id.state', '=', 'posted'],
    ['move_id.journal_id.name', '=', 'Facturas de Proveedores'],
    ['product_id', '!=', False],
    ['date', '>=', '2024-01-01'],
    ['date', '<=', '2024-12-31']
]

lineas_sin_filtro = odoo.search_read(
    'account.move.line',
    domain_base,
    ['id'],
    limit=100000
)
total_sin_filtro = len(lineas_sin_filtro)

print(f"\n📊 Líneas de facturas compra 2024 SIN filtro NC: {total_sin_filtro}")

# Intentar con diferentes filtros
filtros_a_probar = [
    (['move_id.reversed_entry_id', '=', False], "reversed_entry_id = False"),
    (['move_id.payment_state', '!=', 'reversed'], "payment_state != reversed"),
]

for filtro, descripcion in filtros_a_probar:
    try:
        domain = domain_base.copy()
        domain.append(filtro)
        
        lineas = odoo.search_read('account.move.line', domain, ['id'], limit=100000)
        count = len(lineas)
        diferencia = total_sin_filtro - count
        print(f"📊 Con filtro '{descripcion}': {count} líneas (excluye {diferencia})")
    except Exception as e:
        print(f"❌ Filtro '{descripcion}' falló: {str(e)}")

print("\n✅ Análisis completado\n")
