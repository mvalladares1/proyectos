#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analisis de OC09900.
Confirma que la OC debe quedar en USD con precio unitario 1.6 y lista los
registros derivados que se deben revisar o corregir.
"""
import json
import xmlrpc.client


URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

OC_NAME = 'OC09900'
PRECIO_CORRECTO = 1.6
MONEDA_DESTINO = 'USD'


def main() -> None:
    print('=' * 100)
    print(f'ANALISIS DE {OC_NAME}')
    print('=' * 100)

    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    if not uid:
        raise SystemExit('Error de autenticacion')

    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

    oc = models.execute_kw(
        DB,
        uid,
        PASSWORD,
        'purchase.order',
        'search_read',
        [[['name', '=', OC_NAME]]],
        {
            'fields': [
                'id',
                'partner_id',
                'date_order',
                'state',
                'currency_id',
                'amount_total',
                'invoice_status',
                'picking_ids',
                'order_line',
            ],
            'limit': 1,
        },
    )
    if not oc:
        raise SystemExit(f'{OC_NAME} no encontrada')

    oc = oc[0]
    oc_id = oc['id']

    usd = models.execute_kw(
        DB,
        uid,
        PASSWORD,
        'res.currency',
        'search_read',
        [[['name', '=', 'USD']]],
        {'fields': ['id', 'name'], 'limit': 1},
    )
    if not usd:
        raise SystemExit('No se encontro la moneda USD')

    lineas = models.execute_kw(
        DB,
        uid,
        PASSWORD,
        'purchase.order.line',
        'search_read',
        [[['order_id', '=', oc_id]]],
        {
            'fields': [
                'id',
                'product_id',
                'product_qty',
                'qty_received',
                'qty_invoiced',
                'price_unit',
                'price_subtotal',
                'currency_id',
                'move_ids',
            ]
        },
    )

    picking_ids = oc.get('picking_ids', [])
    pickings = models.execute_kw(
        DB,
        uid,
        PASSWORD,
        'stock.picking',
        'search_read',
        [[['id', 'in', picking_ids]]],
        {'fields': ['id', 'name', 'state', 'date_done', 'move_ids']},
    ) if picking_ids else []

    move_ids = sorted({move_id for picking in pickings for move_id in picking.get('move_ids', [])})
    moves = models.execute_kw(
        DB,
        uid,
        PASSWORD,
        'stock.move',
        'search_read',
        [[['id', 'in', move_ids]]],
        {
            'fields': [
                'id',
                'product_id',
                'product_uom_qty',
                'quantity_done',
                'price_unit',
                'state',
                'purchase_line_id',
            ]
        },
    ) if move_ids else []

    related_move_ids = [
        move['id']
        for move in moves
        if move.get('purchase_line_id') and move['purchase_line_id'][0] in {linea['id'] for linea in lineas}
    ]

    layers = models.execute_kw(
        DB,
        uid,
        PASSWORD,
        'stock.valuation.layer',
        'search_read',
        [[['stock_move_id', 'in', related_move_ids]]],
        {
            'fields': [
                'id',
                'quantity',
                'unit_cost',
                'value',
                'remaining_qty',
                'remaining_value',
                'currency_id',
                'stock_move_id',
                'description',
            ]
        },
    ) if related_move_ids else []

    facturas = models.execute_kw(
        DB,
        uid,
        PASSWORD,
        'account.move',
        'search_read',
        [[['invoice_origin', '=', OC_NAME]]],
        {
            'fields': ['id', 'name', 'state', 'move_type', 'amount_total', 'currency_id'],
            'limit': 20,
        },
    )

    print(f'OC ID: {oc_id}')
    print(f"Proveedor: {oc['partner_id'][1] if oc['partner_id'] else 'N/A'}")
    print(f"Estado: {oc['state']}")
    print(f"Moneda actual: {oc['currency_id'][1]} (ID {oc['currency_id'][0]})")
    print(f"Moneda destino: {usd[0]['name']} (ID {usd[0]['id']})")
    print(f"Total actual: {oc['amount_total']}")
    print(f"Estado facturacion: {oc['invoice_status']}")
    print()

    print('Lineas de compra:')
    for linea in lineas:
        print(json.dumps(linea, ensure_ascii=False, indent=2))

    print('\nRecepciones:')
    for picking in pickings:
        print(json.dumps(picking, ensure_ascii=False, indent=2))

    print('\nMovimientos relacionados:')
    for move in moves:
        print(json.dumps(move, ensure_ascii=False, indent=2))

    print('\nCapas de valoracion relacionadas:')
    for layer in layers:
        print(json.dumps(layer, ensure_ascii=False, indent=2))
        if abs(layer['unit_cost'] - PRECIO_CORRECTO) >= 0.0001:
            valor_correcto = layer['quantity'] * PRECIO_CORRECTO
            print(
                f"  -> Layer {layer['id']} requiere costo {PRECIO_CORRECTO} y valor {valor_correcto} {MONEDA_DESTINO}"
            )

    print('\nFacturas relacionadas:')
    if facturas:
        for factura in facturas:
            print(json.dumps(factura, ensure_ascii=False, indent=2))
    else:
        print('Sin facturas relacionadas')

    print('\nResumen operativo:')
    print('- Cambiar currency_id de purchase.order a USD')
    print('- Cambiar currency_id de purchase.order.line a USD y mantener price_unit=1.6')
    print('- Verificar stock.move ligados a la linea; el precio ya figura en 1.6')
    print('- Corregir unit_cost/value de stock.valuation.layer; currency_id es readonly en Odoo y seguira en CLP')


if __name__ == '__main__':
    main()