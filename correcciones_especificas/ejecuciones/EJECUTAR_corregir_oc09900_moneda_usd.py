#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Correccion especifica de OC09900.
Objetivo: dejar la OC y su linea en USD con precio 1.6, y ajustar la capa de
valoracion generada para que quede consistente con ese precio y moneda.
"""
import json
import xmlrpc.client
from datetime import datetime
from pathlib import Path


URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

OC_ID = 9908
OC_NAME = 'OC09900'
USD_ID = 2
PRECIO_CORRECTO = 1.6

LINEA_CONFIG = {
    'linea_id': 16374,
    'precio_nuevo': PRECIO_CORRECTO,
    'moves_ids': [144062, 144205],
    'layers_ids': [82191],
}


def read_one(models, model, record_id, fields, uid):
    records = models.execute_kw(DB, uid, PASSWORD, model, 'read', [[record_id]], {'fields': fields})
    if not records:
        raise ValueError(f'No se encontro {model} con id {record_id}')
    return records[0]


def save_log(log_data):
    filename = Path(__file__).with_name(
        f"oc09900_moneda_usd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    filename.write_text(json.dumps(log_data, indent=2, ensure_ascii=False), encoding='utf-8')
    return filename


def main() -> None:
    print('=' * 100)
    print(f'CORRECCION REAL {OC_NAME}: CLP -> USD con precio {PRECIO_CORRECTO}')
    print('=' * 100)

    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    if not uid:
        raise SystemExit('Error de autenticacion')

    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    print(f'Conectado con uid={uid}')

    log = {
        'fecha_ejecucion': datetime.now().isoformat(),
        'oc': OC_NAME,
        'oc_id': OC_ID,
        'objetivo': {
            'currency_id': USD_ID,
            'price_unit': PRECIO_CORRECTO,
        },
        'cambios': [],
        'errores': [],
    }

    try:
        facturas = models.execute_kw(
            DB,
            uid,
            PASSWORD,
            'account.move',
            'search_read',
            [[['invoice_origin', '=', OC_NAME], ['state', '=', 'draft']]],
            {'fields': ['id', 'name', 'state'], 'limit': 20},
        )
        if facturas:
            for factura in facturas:
                print(f"Eliminando factura borrador {factura['name']} ({factura['id']})")
                models.execute_kw(DB, uid, PASSWORD, 'account.move', 'unlink', [[factura['id']]])
                log['cambios'].append({
                    'tipo': 'factura_borrador_eliminada',
                    'id': factura['id'],
                    'nombre': factura['name'],
                })
        else:
            print('No hay facturas borrador asociadas')

        oc_antes = read_one(models, 'purchase.order', OC_ID, ['currency_id', 'amount_total'], uid)
        print(
            f"OC antes: moneda={oc_antes['currency_id'][1] if oc_antes['currency_id'] else 'N/A'} total={oc_antes['amount_total']}"
        )

        if not oc_antes.get('currency_id') or oc_antes['currency_id'][0] != USD_ID:
            result = models.execute_kw(
                DB,
                uid,
                PASSWORD,
                'purchase.order',
                'write',
                [[OC_ID], {'currency_id': USD_ID}],
            )
            if not result:
                raise RuntimeError('No se pudo actualizar currency_id de purchase.order')
            log['cambios'].append({
                'tipo': 'purchase.order',
                'id': OC_ID,
                'campo': 'currency_id',
                'antes': oc_antes.get('currency_id'),
                'despues': [USD_ID, 'USD'],
            })

        linea_id = LINEA_CONFIG['linea_id']
        linea_antes = read_one(
            models,
            'purchase.order.line',
            linea_id,
            ['currency_id', 'price_unit', 'product_qty', 'price_subtotal', 'product_id'],
            uid,
        )
        print(
            f"Linea antes {linea_id}: moneda={linea_antes['currency_id'][1]} precio={linea_antes['price_unit']}"
        )

        valores_linea = {}
        if linea_antes.get('currency_id') and linea_antes['currency_id'][0] != USD_ID:
            valores_linea['currency_id'] = USD_ID
        if abs(linea_antes['price_unit'] - PRECIO_CORRECTO) >= 0.0001:
            valores_linea['price_unit'] = PRECIO_CORRECTO

        if valores_linea:
            result = models.execute_kw(
                DB,
                uid,
                PASSWORD,
                'purchase.order.line',
                'write',
                [[linea_id], valores_linea],
            )
            if not result:
                raise RuntimeError('No se pudo actualizar purchase.order.line')
            log['cambios'].append({
                'tipo': 'purchase.order.line',
                'id': linea_id,
                'antes': {
                    'currency_id': linea_antes.get('currency_id'),
                    'price_unit': linea_antes['price_unit'],
                },
                'despues': valores_linea,
            })
        else:
            print('La linea ya estaba con precio correcto; solo se validara el resultado')

        for move_id in LINEA_CONFIG['moves_ids']:
            move_antes = read_one(
                models,
                'stock.move',
                move_id,
                ['price_unit', 'quantity_done', 'state', 'product_id'],
                uid,
            )
            if abs(move_antes['price_unit'] - PRECIO_CORRECTO) >= 0.0001:
                result = models.execute_kw(
                    DB,
                    uid,
                    PASSWORD,
                    'stock.move',
                    'write',
                    [[move_id], {'price_unit': PRECIO_CORRECTO}],
                )
                if not result:
                    raise RuntimeError(f'No se pudo actualizar stock.move {move_id}')
                log['cambios'].append({
                    'tipo': 'stock.move',
                    'id': move_id,
                    'antes': {'price_unit': move_antes['price_unit'], 'state': move_antes['state']},
                    'despues': {'price_unit': PRECIO_CORRECTO},
                })

        layer_currency_info = models.execute_kw(
            DB,
            uid,
            PASSWORD,
            'stock.valuation.layer',
            'fields_get',
            [['currency_id']],
            {'attributes': ['readonly', 'store']},
        )
        layer_currency_readonly = layer_currency_info['currency_id']['readonly']

        if layer_currency_readonly:
            log['cambios'].append({
                'tipo': 'info',
                'detalle': 'stock.valuation.layer.currency_id es readonly/store=False y no puede corregirse por XML-RPC',
            })

        for layer_id in LINEA_CONFIG['layers_ids']:
            layer_antes = read_one(
                models,
                'stock.valuation.layer',
                layer_id,
                ['quantity', 'unit_cost', 'value', 'remaining_qty', 'remaining_value', 'currency_id'],
                uid,
            )
            valor_corregido = layer_antes['quantity'] * PRECIO_CORRECTO
            valores_layer = {}

            if abs(layer_antes['unit_cost'] - PRECIO_CORRECTO) >= 0.0001:
                valores_layer['unit_cost'] = PRECIO_CORRECTO
            if abs(layer_antes['value'] - valor_corregido) >= 0.0001:
                valores_layer['value'] = valor_corregido
            if layer_antes.get('remaining_qty'):
                remaining_value_corregido = layer_antes['remaining_qty'] * PRECIO_CORRECTO
                if abs(layer_antes.get('remaining_value', 0.0) - remaining_value_corregido) >= 0.0001:
                    valores_layer['remaining_value'] = remaining_value_corregido

            if valores_layer:
                result = models.execute_kw(
                    DB,
                    uid,
                    PASSWORD,
                    'stock.valuation.layer',
                    'write',
                    [[layer_id], valores_layer],
                )
                if not result:
                    raise RuntimeError(f'No se pudo actualizar stock.valuation.layer {layer_id}')
                log['cambios'].append({
                    'tipo': 'stock.valuation.layer',
                    'id': layer_id,
                    'antes': {
                        'currency_id': layer_antes.get('currency_id'),
                        'unit_cost': layer_antes['unit_cost'],
                        'value': layer_antes['value'],
                        'remaining_value': layer_antes.get('remaining_value'),
                    },
                    'despues': valores_layer,
                })

        oc_despues = read_one(models, 'purchase.order', OC_ID, ['currency_id', 'amount_total'], uid)
        linea_despues = read_one(
            models,
            'purchase.order.line',
            linea_id,
            ['currency_id', 'price_unit', 'price_subtotal'],
            uid,
        )
        layer_despues = read_one(
            models,
            'stock.valuation.layer',
            LINEA_CONFIG['layers_ids'][0],
            ['currency_id', 'unit_cost', 'value'],
            uid,
        )

        log['verificacion_final'] = {
            'purchase.order': oc_despues,
            'purchase.order.line': linea_despues,
            'stock.valuation.layer': layer_despues,
        }

        print('Verificacion final:')
        print(json.dumps(log['verificacion_final'], ensure_ascii=False, indent=2))

        log_path = save_log(log)
        print(f'Log guardado en: {log_path}')
    except Exception as exc:
        log['errores'].append(str(exc))
        log_path = save_log(log)
        print(f'ERROR: {exc}')
        print(f'Log guardado en: {log_path}')
        raise


if __name__ == '__main__':
    main()