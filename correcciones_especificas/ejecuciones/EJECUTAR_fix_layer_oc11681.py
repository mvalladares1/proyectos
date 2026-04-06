#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORRECCIÓN OC11681 - FIX LAYER CURRENCY
Corregir la moneda de la capa de valoración que quedó en CLP
"""
import xmlrpc.client
import json
from datetime import datetime

# Configuración
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Datos
LAYER_ID = 90074
MONEDA_USD = 2

print("="*80)
print(f"CORRECCIÓN LAYER 90074 - CAMBIO DE MONEDA CLP → USD")
print("="*80)

try:
    # Conectar
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        raise Exception("❌ Error de autenticación")
    
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    print("✅ Conectado a Odoo\n")
    
    # Leer estado actual del layer
    layer_antes = models.execute_kw(db, uid, password,
        'stock.valuation.layer', 'read',
        [LAYER_ID],
        {'fields': ['id', 'currency_id', 'unit_cost', 'value', 'quantity', 'product_id']})[0]
    
    print(f"Layer {LAYER_ID} - Estado actual:")
    print(f"  Producto: {layer_antes['product_id'][1]}")
    print(f"  Moneda: {layer_antes['currency_id'][1]} (ID: {layer_antes['currency_id'][0]})")
    print(f"  Cantidad: {layer_antes['quantity']}")
    print(f"  Costo unitario: ${layer_antes['unit_cost']:,.2f}")
    print(f"  Valor total: ${layer_antes['value']:,.2f}\n")
    
    if layer_antes['currency_id'][0] == MONEDA_USD:
        print("✓ La moneda ya está en USD, no se requiere cambio")
    else:
        print(f"Cambiando moneda de {layer_antes['currency_id'][1]} a USD...\n")
        
        # Intentar cambiar la moneda
        result = models.execute_kw(db, uid, password,
            'stock.valuation.layer', 'write',
            [[LAYER_ID], {'currency_id': MONEDA_USD}])
        
        print(f"Resultado de write: {result}\n")
        
        # Verificar el cambio
        layer_despues = models.execute_kw(db, uid, password,
            'stock.valuation.layer', 'read',
            [LAYER_ID],
            {'fields': ['id', 'currency_id', 'unit_cost', 'value', 'quantity']})[0]
        
        print(f"Layer {LAYER_ID} - Después del cambio:")
        print(f"  Moneda: {layer_despues['currency_id'][1]} (ID: {layer_despues['currency_id'][0]})")
        print(f"  Costo unitario: ${layer_despues['unit_cost']:,.2f}")
        print(f"  Valor total: ${layer_despues['value']:,.2f}\n")
        
        if layer_despues['currency_id'][0] == MONEDA_USD:
            print("="*80)
            print("✅ CORRECCIÓN COMPLETADA - Moneda cambiada a USD")
            print("="*80)
        else:
            print("="*80)
            print("❌ ADVERTENCIA - La moneda no cambió")
            print("="*80)
            print("Puede ser que el campo currency_id esté protegido o sea de solo lectura")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
