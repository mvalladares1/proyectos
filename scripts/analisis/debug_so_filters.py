import xmlrpc.client

URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

fecha_inicio = "2026-01-01"
fecha_fin = "2026-09-30"

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")


def count(domain, label):
    c = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search_count', [domain])
    print(f"{label}: {c}")
    return c

base = [('state', 'in', ['draft', 'sent', 'sale'])]
count(base, 'base state draft/sent/sale')

count(base + [('invoice_status', '!=', 'invoiced')], ' + invoice_status != invoiced')
count(base + [('invoice_ids', '=', False)], ' + invoice_ids = False')

count(base + [
    ('x_studio_fecha_tentativa_de_pago', '!=', False),
    ('x_studio_fecha_tentativa_de_pago', '>=', fecha_inicio),
    ('x_studio_fecha_tentativa_de_pago', '<=', fecha_fin),
], ' + tentative date in range')

count(base + [
    ('date_order', '>=', fecha_inicio),
    ('date_order', '<=', fecha_fin),
], ' + date_order in range')

or_domain = base + [
    '|',
        '&',
            ('x_studio_fecha_tentativa_de_pago', '!=', False),
            ('x_studio_fecha_tentativa_de_pago', '>=', fecha_inicio),
            ('x_studio_fecha_tentativa_de_pago', '<=', fecha_fin),
        '&',
            ('x_studio_fecha_tentativa_de_pago', '=', False),
            ('date_order', '>=', fecha_inicio),
            ('date_order', '<=', fecha_fin)
]
count(or_domain, ' + OR tentative/date_order in range')

full = [
    ('state', 'in', ['draft', 'sent', 'sale']),
    ('invoice_status', '!=', 'invoiced'),
    '|',
        '&',
            ('x_studio_fecha_tentativa_de_pago', '!=', False),
            ('x_studio_fecha_tentativa_de_pago', '>=', fecha_inicio),
            ('x_studio_fecha_tentativa_de_pago', '<=', fecha_fin),
        '&',
            ('x_studio_fecha_tentativa_de_pago', '=', False),
            ('date_order', '>=', fecha_inicio),
            ('date_order', '<=', fecha_fin)
]
count(full, 'FULL domain actual')

sample = models.execute_kw(
    DB, uid, PASSWORD,
    'sale.order', 'search_read',
    [full],
    {'fields': ['name', 'state', 'invoice_status', 'x_studio_fecha_tentativa_de_pago', 'date_order'], 'limit': 20}
)
print('\nSample full domain:', len(sample))
for s in sample[:10]:
    print(s)
