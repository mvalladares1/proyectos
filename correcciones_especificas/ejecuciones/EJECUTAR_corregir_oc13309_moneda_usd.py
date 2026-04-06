#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Correccion especifica de OC13309.

Objetivo:
- Cambiar purchase.order y purchase.order.line de CLP a USD.
- Dejar price_unit en 1.4 USD.
- Ajustar stock.move relacionado si el precio esta desalineado.
- Ajustar stock.valuation.layer en unit_cost/value/remaining_value.

Nota: stock.valuation.layer.currency_id es readonly/store=False en Odoo y no se
puede forzar por XML-RPC.
"""
import json
import xmlrpc.client
from datetime import datetime
from pathlib import Path


URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

OC_CONFIG = {
    'name': 'OC13309',
    'oc_id': 13319,
    'price_unit': 1.4,
    'line_id': 21948,
    'move_ids': [171643],
    'layer_ids': [103777],
}


def read_one(models, uid, model, record_id, fields):
    records = models.execute_kw(DB, uid, PASSWORD, model, 'read', [[record_id]], {'fields': fields})
    if not records:
        raise ValueError(f'No se encontro {model} con id {record_id}')
    return records[0]


def save_log(log_data):
    filename = Path(__file__).with_name(
        f"oc13309_moneda_usd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    filename.write_text(json.dumps(log_data, indent=2, ensure_ascii=False), encoding='utf-8')
    return filename


def main() -> None:
    print('=' * 110)
    print('CORRECCION REAL OC13309: CLP -> USD, precio 1.4')
    print('=' * 110)

    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    if not uid:
        raise SystemExit('Error de autenticacion')

    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

    usd_currency = models.execute_kw(
        DB,
        uid,
        PASSWORD,
        'res.currency',
        'search_read',
        [[['name', '=', 'USD']]],
        {'fields': ['id', 'name'], 'limit': 1},
    )
    if not usd_currency:
        raise SystemExit('No se encontro la moneda USD')

    usd_id = usd_currency[0]['id']

    layer_currency_info = models.execute_kw(
        DB,
        uid,
        PASSWORD,
        'stock.valuation.layer',
        'fields_get',
        [['currency_id']],
        {'attributes': ['readonly', 'store']},
    )

    log = {
        'fecha_ejecucion': datetime.now().isoformat(),
        'oc': OC_CONFIG['name'],
        'currency_id_destino': usd_id,
        'currency_note': layer_currency_info,
        'cambios': [],
        'errores': [],
    }

    try:
        draft_invoices = models.execute_kw(
            DB,
            uid,
            PASSWORD,
            'account.move',
            'search_read',
            [[['invoice_origin', '=', OC_CONFIG['name']], ['state', '=', 'draft']]],
            {'fields': ['id', 'name', 'state'], 'limit': 20},
        )
        if draft_invoices:
            for invoice in draft_invoices:
                models.execute_kw(DB, uid, PASSWORD, 'account.move', 'unlink', [[invoice['id']]])
                log['cambios'].append({
                    'tipo': 'factura_borrador_eliminada',
                    'id': invoice['id'],
                    'nombre': invoice['name'],
                })
        else:
            print('Sin facturas borrador relacionadas')

        oc_before = read_one(models, uid, 'purchase.order', OC_CONFIG['oc_id'], ['currency_id', 'amount_total'])
        if not oc_before.get('currency_id') or oc_before['currency_id'][0] != usd_id:
            result = models.execute_kw(
                DB,
                uid,
                PASSWORD,
                'purchase.order',
                'write',
                [[OC_CONFIG['oc_id']], {'currency_id': usd_id}],
            )
            if not result:
                raise RuntimeError('No se pudo actualizar purchase.order')
            log['cambios'].append({
                'tipo': 'purchase.order',
                'id': OC_CONFIG['oc_id'],
                'antes': oc_before,
                'despues': {'currency_id': [usd_id, 'USD']},
            })
        print(
            f"OC: moneda {oc_before['currency_id'][1] if oc_before.get('currency_id') else 'N/A'} -> USD | total={oc_before['amount_total']}"
        )

        line_before = read_one(
            models,
            uid,
            'purchase.order.line',
            OC_CONFIG['line_id'],
            ['currency_id', 'price_unit', 'price_subtotal', 'product_qty', 'product_id'],
        )
        line_updates = {}
        if line_before.get('currency_id') and line_before['currency_id'][0] != usd_id:
            line_updates['currency_id'] = usd_id
        if abs(line_before['price_unit'] - OC_CONFIG['price_unit']) >= 0.0001:
            line_updates['price_unit'] = OC_CONFIG['price_unit']

        if line_updates:
            result = models.execute_kw(
                DB,
                uid,
                PASSWORD,
                'purchase.order.line',
                'write',
                [[OC_CONFIG['line_id']], line_updates],
            )
            if not result:
                raise RuntimeError('No se pudo actualizar purchase.order.line')
            log['cambios'].append({
                'tipo': 'purchase.order.line',
                'id': OC_CONFIG['line_id'],
                'antes': line_before,
                'despues': line_updates,
            })
        print(
            f"Linea {OC_CONFIG['line_id']}: moneda {line_before['currency_id'][1]} | precio {line_before['price_unit']}"
        )

        for move_id in OC_CONFIG['move_ids']:
            move_before = read_one(
                models,
                uid,
                'stock.move',
                move_id,
                ['price_unit', 'quantity_done', 'state', 'product_id'],
            )
            if abs(move_before['price_unit'] - OC_CONFIG['price_unit']) >= 0.0001:
                result = models.execute_kw(
                    DB,
                    uid,
                    PASSWORD,
                    'stock.move',
                    'write',
                    [[move_id], {'price_unit': OC_CONFIG['price_unit']}],
                )
                if not result:
                    raise RuntimeError(f'No se pudo actualizar stock.move {move_id}')
                log['cambios'].append({
                    'tipo': 'stock.move',
                    'id': move_id,
                    'antes': move_before,
                    'despues': {'price_unit': OC_CONFIG['price_unit']},
                })
            print(
                f"Move {move_id}: state={move_before['state']} qty_done={move_before['quantity_done']} price_unit={move_before['price_unit']}"
            )

        for layer_id in OC_CONFIG['layer_ids']:
            layer_before = read_one(
                models,
                uid,
                'stock.valuation.layer',
                layer_id,
                ['quantity', 'unit_cost', 'value', 'remaining_qty', 'remaining_value', 'currency_id'],
            )
            corrected_value = layer_before['quantity'] * OC_CONFIG['price_unit']
            layer_updates = {}
            if abs(layer_before['unit_cost'] - OC_CONFIG['price_unit']) >= 0.0001:
                layer_updates['unit_cost'] = OC_CONFIG['price_unit']
            if abs(layer_before['value'] - corrected_value) >= 0.0001:
                layer_updates['value'] = corrected_value
            if layer_before.get('remaining_qty'):
                corrected_remaining = layer_before['remaining_qty'] * OC_CONFIG['price_unit']
                if abs(layer_before.get('remaining_value', 0.0) - corrected_remaining) >= 0.0001:
                    layer_updates['remaining_value'] = corrected_remaining

            if layer_updates:
                result = models.execute_kw(
                    DB,
                    uid,
                    PASSWORD,
                    'stock.valuation.layer',
                    'write',
                    [[layer_id], layer_updates],
                )
                if not result:
                    raise RuntimeError(f'No se pudo actualizar stock.valuation.layer {layer_id}')
                log['cambios'].append({
                    'tipo': 'stock.valuation.layer',
                    'id': layer_id,
                    'antes': layer_before,
                    'despues': layer_updates,
                })
            print(
                f"Layer {layer_id}: currency={layer_before['currency_id'][1] if layer_before.get('currency_id') else 'N/A'} unit_cost={layer_before['unit_cost']} value={layer_before['value']}"
            )

        verification = {
            'purchase.order': read_one(models, uid, 'purchase.order', OC_CONFIG['oc_id'], ['name', 'currency_id', 'amount_total']),
            'purchase.order.line': read_one(models, uid, 'purchase.order.line', OC_CONFIG['line_id'], ['currency_id', 'price_unit', 'price_subtotal', 'product_qty']),
            'stock.moves': [
                read_one(models, uid, 'stock.move', move_id, ['price_unit', 'quantity_done', 'state'])
                for move_id in OC_CONFIG['move_ids']
            ],
            'stock.valuation.layers': [
                read_one(models, uid, 'stock.valuation.layer', layer_id, ['currency_id', 'unit_cost', 'value', 'remaining_qty', 'remaining_value'])
                for layer_id in OC_CONFIG['layer_ids']
            ],
        }
        log['cambios'].append({'tipo': 'verificacion_final', 'data': verification})

        print('Verificacion final:')
        print(json.dumps(verification, ensure_ascii=False, indent=2))
    except Exception as exc:
        log['errores'].append({'oc': OC_CONFIG['name'], 'error': str(exc)})
        print(f"ERROR en {OC_CONFIG['name']}: {exc}")

    log_path = save_log(log)
    print('\n' + '=' * 110)
    print(f'Log guardado en: {log_path}')
    print('=' * 110)

    if log['errores']:
        raise SystemExit('La ejecucion termino con errores; revisar log.')


if __name__ == '__main__':
    main()