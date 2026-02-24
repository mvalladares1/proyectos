from shared.odoo_client import OdooClient


def main():
    odoo = OdooClient(username='api_user', password='rf2025api')
    print('OK auth')

    moves = odoo.search_read(
        'account.move',
        [['journal_id', '=', 130], ['move_type', 'in', ['in_invoice', 'in_refund']]],
        ['id', 'name', 'line_ids', 'partner_id', 'invoice_date_due', 'date'],
        limit=5
    )
    print('moves', len(moves))
    for m in moves:
        print('move', m['id'], m.get('name'), 'lines', len(m.get('line_ids', [])))

    fields_meta = odoo.execute('account.move.line', 'fields_get', [], ['string', 'type'])
    keys = sorted([
        k for k in fields_meta.keys()
        if ('ifrs' in k.lower() or 'analytic' in k.lower() or 'analit' in k.lower())
    ])
    print('candidate_fields_count account.move.line', len(keys))
    for k in keys[:120]:
        meta = fields_meta.get(k, {})
        print(k, '|', meta.get('string'), '|', meta.get('type'))

    if moves:
        line_ids = []
        for m in moves:
            line_ids.extend(m.get('line_ids', [])[:8])
        line_ids = list(dict.fromkeys(line_ids))[:30]

        candidate_fields = ['id', 'name', 'move_id', 'account_id', 'analytic_account_id', 'analytic_distribution']
        for field in ['x_studio_cat_ifrs_3', 'x_studio_categora_ifrs', 'x_studio_cat_ifrs_2_vf', 'x_studio_cat_ifrs_4']:
            if field in fields_meta:
                candidate_fields.append(field)

        lines = odoo.read('account.move.line', line_ids, candidate_fields)
        print('sample_lines', len(lines), 'fields', candidate_fields)
        for row in lines[:10]:
            print({k: row.get(k) for k in candidate_fields})

    acc_meta = odoo.execute('account.account', 'fields_get', [], ['string', 'type'])
    acc_keys = sorted([
        k for k in acc_meta.keys()
        if ('ifrs' in k.lower() or 'analytic' in k.lower() or 'analit' in k.lower())
    ])
    print('candidate_fields_count account.account', len(acc_keys))
    for k in acc_keys[:120]:
        meta = acc_meta.get(k, {})
        print(k, '|', meta.get('string'), '|', meta.get('type'))

    # Leer cuentas de las líneas para ver dónde vive IFRS3
    account_ids = []
    if moves:
        for m in moves:
            if m.get('line_ids'):
                lines = odoo.read('account.move.line', m['line_ids'][:20], ['id', 'account_id'])
                for l in lines:
                    acc = l.get('account_id')
                    if isinstance(acc, (list, tuple)) and acc:
                        account_ids.append(acc[0])
    account_ids = list(dict.fromkeys(account_ids))[:30]

    if account_ids:
        account_fields = ['id', 'code', 'name']
        for field in ['x_studio_cat_ifrs_3', 'x_studio_categora_ifrs', 'x_studio_cat_ifrs_2_vf', 'x_studio_cat_ifrs_4']:
            if field in acc_meta:
                account_fields.append(field)
        accounts = odoo.read('account.account', account_ids, account_fields)
        print('sample_accounts', len(accounts), 'fields', account_fields)
        for a in accounts[:10]:
            print({k: a.get(k) for k in account_fields})


if __name__ == '__main__':
    main()
