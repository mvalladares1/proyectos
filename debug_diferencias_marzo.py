import xmlrpc.client
from datetime import datetime, timedelta
from collections import defaultdict

# Conexión a Odoo
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 100)
print("ANÁLISIS DETALLADO DE DIFERENCIAS EN MARZO 2026")
print("=" * 100)

# Definir las semanas de marzo
semanas_marzo = {
    'S10': ('2026-03-02', '2026-03-08'),
    'S11': ('2026-03-09', '2026-03-15'),
    'S12': ('2026-03-16', '2026-03-22'),
    'S13': ('2026-03-23', '2026-03-29'),
}

def get_facturas_cliente(fecha_inicio, fecha_fin):
    """Obtener facturas de cliente"""
    domain = [
        ('move_type', '=', 'out_invoice'),
        ('state', '=', 'posted'),
        ('invoice_date', '>=', fecha_inicio),
        ('invoice_date', '<=', fecha_fin),
    ]
    fields = ['id', 'name', 'invoice_date', 'date', 'amount_total', 'amount_residual', 'payment_state']
    return models.execute_kw(db, uid, password, 'account.move', 'search_read', [domain], {'fields': fields, 'limit': 20000})

def get_facturas_proveedor(fecha_inicio, fecha_fin):
    """Obtener facturas de proveedor"""
    domain = [
        ('move_type', '=', 'in_invoice'),
        ('state', '=', 'posted'),
        ('invoice_date', '>=', fecha_inicio),
        ('invoice_date', '<=', fecha_fin),
    ]
    fields = ['id', 'name', 'invoice_date', 'date', 'amount_total', 'amount_residual', 'payment_state', 'x_studio_fecha_estimada_de_pago', 'invoice_date_due']
    return models.execute_kw(db, uid, password, 'account.move', 'search_read', [domain], {'fields': fields, 'limit': 20000})

# Comparar para cada semana
for semana, (inicio, fin) in semanas_marzo.items():
    print(f"\n{'=' * 100}")
    print(f"SEMANA {semana}: {inicio} a {fin}")
    print(f"{'=' * 100}")
    
    # Obtener facturas de cliente
    facturas_cliente = get_facturas_cliente(inicio, fin)
    print(f"\n📊 FACTURAS CLIENTE ({len(facturas_cliente)} facturas)")
    print(f"{'ID':<15} {'Nombre':<20} {'Fecha Factura':<15} {'Fecha Contable':<15} {'Total':<15} {'Residual':<15} {'Estado Pago':<15}")
    print("-" * 120)
    
    total_cobros = 0
    for f in facturas_cliente:
        fecha_factura = f.get('invoice_date', 'N/A')
        fecha_contable = f.get('date', 'N/A')
        total = f.get('amount_total', 0)
        residual = f.get('amount_residual', 0)
        estado = f.get('payment_state', 'N/A')
        
        # Solo contar las PAGADAS (residual = 0)
        if residual == 0:
            total_cobros += total
            print(f"{f['id']:<15} {f['name']:<20} {fecha_factura:<15} {fecha_contable:<15} ${total:>13,.0f} ${residual:>13,.0f} {estado:<15}")
    
    print(f"\n✅ TOTAL COBROS (pagadas): ${total_cobros:,.0f}")
    
    # Obtener facturas de proveedor
    facturas_proveedor = get_facturas_proveedor(inicio, fin)
    print(f"\n📊 FACTURAS PROVEEDOR ({len(facturas_proveedor)} facturas)")
    print(f"{'ID':<10} {'Nombre':<15} {'Fech.Fact':<12} {'Fech.Cont':<12} {'Fech.Est':<12} {'Fech.Venc':<12} {'Total':<15} {'Residual':<15} {'Estado':<10}")
    print("-" * 140)
    
    total_pagadas = 0
    total_no_pagadas = 0
    
    for f in facturas_proveedor:
        fecha_factura = f.get('invoice_date', 'N/A')
        fecha_contable = f.get('date', 'N/A')
        fecha_estimada = f.get('x_studio_fecha_estimada_de_pago', 'N/A')
        fecha_venc = f.get('invoice_date_due', 'N/A')
        total = f.get('amount_total', 0)
        residual = f.get('amount_residual', 0)
        estado = f.get('payment_state', 'N/A')
        
        # Clasificar según payment_state
        if residual == 0:
            total_pagadas += total
            marca = "✓ PAG"
        else:
            total_no_pagadas += total
            marca = "✗ NOPAG"
        
        print(f"{f['id']:<10} {f['name']:<15} {str(fecha_factura):<12} {str(fecha_contable):<12} {str(fecha_estimada):<12} {str(fecha_venc):<12} ${total:>13,.0f} ${residual:>13,.0f} {marca:<10}")
    
    print(f"\n✅ TOTAL PAGADAS: -${total_pagadas:,.0f}")
    print(f"❌ TOTAL NO PAGADAS: -${total_no_pagadas:,.0f}")
    print(f"📊 TOTAL PAGOS: -${total_pagadas + total_no_pagadas:,.0f}")

print("\n" + "=" * 100)
print("ANÁLISIS COMPLETADO")
print("=" * 100)
