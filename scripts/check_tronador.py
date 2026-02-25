import json
import sys

d = json.load(open(sys.argv[1]))
for act_name, act_data in d.get('actividades', {}).items():
    for concepto in act_data.get('conceptos', []):
        if concepto.get('id') == '1.1.1':
            print(f"=== CONCEPTO 1.1.1 ===")
            cuentas = concepto.get('cuentas', [])
            print(f"Num cuentas: {len(cuentas)}")
            for i, cuenta in enumerate(cuentas):
                nombre_cuenta = cuenta.get('nombre', '')
                codigo = cuenta.get('codigo', '')
                es_cxc = cuenta.get('es_cuenta_cxc', False)
                print(f"\nCuenta {i}: {codigo} - {nombre_cuenta} (es_cuenta_cxc={es_cxc})")
                etiquetas = cuenta.get('etiquetas', [])
                print(f"  Num etiquetas: {len(etiquetas)}")
                for j, etq in enumerate(etiquetas):
                    etq_nombre = etq.get('nombre', '')
                    etq_monto = etq.get('monto', 0)
                    facturas = etq.get('facturas', [])
                    sub_etiquetas = etq.get('sub_etiquetas', [])
                    print(f"  Etiqueta {j}: {etq_nombre} (monto={etq_monto}, facturas={len(facturas)}, sub_etiquetas={len(sub_etiquetas)})")
                    
                    # check sub_etiquetas for TRONADOR
                    for se in sub_etiquetas:
                        sename = se.get('nombre', '')
                        if 'TRONADOR' in sename.upper():
                            print(f"    *** TRONADOR IN SUB_ETIQUETA ***")
                            print(f"    nombre: {sename}")
                            print(f"    monto: {se.get('monto')}")
                            montos = se.get('montos_por_mes', {})
                            for m, v in montos.items():
                                if v != 0:
                                    print(f"      {m}: {v}")
                    
                    # check facturas for TRONADOR
                    for f in facturas:
                        fname = f.get('nombre', '')
                        if 'TRONADOR' in fname.upper():
                            print(f"    *** TRONADOR IN FACTURA ***")
                            print(f"    nombre: {fname}")
                            print(f"    monto: {f.get('monto')}")
                            print(f"    categoria: {f.get('categoria')}")

