"""Debug específico para FCXE 000281 - entender líneas duplicadas."""

import sys
sys.path.append('.')

from shared.odoo_client import OdooClient

def main():
    odoo = OdooClient()
    
    # Buscar todas las líneas de la factura FCXE 000281
    lines = odoo.search_read(
        'account.move.line',
        [
            ['move_id.name', '=', 'FCXE 000281'],
            ['move_id.move_type', '=', 'out_invoice']
        ],
        ['product_id', 'quantity', 'price_unit', 'price_subtotal', 'display_type', 'exclude_from_invoice_tab', 'name', 'account_id'],
        limit=50
    )
    
    print(f"Total líneas en FCXE 000281: {len(lines)}\n")
    print(f"{'Descripción':<60} {'Qty':>10} {'P.Unit':>12} {'Subtotal':>15} {'Display':<15} {'Exclude':<8} {'Account':<30}")
    print("-" * 170)
    
    for line in lines:
        nombre = str(line.get('name', ''))[:60]
        qty = line.get('quantity', 0)
        unit = line.get('price_unit', 0)
        subtotal = line.get('price_subtotal', 0)
        display = str(line.get('display_type') or '-')
        exclude = str(line.get('exclude_from_invoice_tab', False))
        
        account = line.get('account_id')
        if isinstance(account, (list, tuple)) and len(account) > 1:
            account_name = account[1][:30]
        else:
            account_name = str(account)[:30]
        
        print(f"{nombre:<60} {qty:>10.2f} {unit:>12.2f} {subtotal:>15,.2f} {display:<15} {exclude:<8} {account_name:<30}")

if __name__ == '__main__':
    main()
