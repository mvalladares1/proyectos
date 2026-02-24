import pathlib, re, sys

pages_dir = pathlib.Path('pages')
sub_dirs = {
    '1_Recepciones.py': 'recepciones',
    '2_Produccion.py': 'produccion',
    '3_Bandejas.py': 'bandejas',
    '4_Stock.py': None,
    '5_Pedidos_Venta.py': 'pedidos',
    '6_Finanzas.py': 'finanzas',
    '7_Rendimiento.py': 'rendimiento',
    '8_Compras.py': 'compras',
    '9_Permisos.py': 'permisos',
    '10_Automatizaciones.py': 'automatizaciones',
    '11_Relacion_Comercial.py': 'relacion_comercial',
    '12_Reconciliacion_Produccion.py': 'reconciliacion',
}

def get_tabs(path):
    content = path.read_text(encoding='utf-8', errors='ignore')
    # Find st.tabs calls
    tab_calls = re.findall(r'st\.tabs\(\s*\[([^\]]+)\]', content)
    all_tabs = []
    for call in tab_calls:
        names = re.findall(r'["\']([\w\s\U00010000-\U0010ffff\u0080-\uFFFF/:,\-\.\(\)]+)["\']', call)
        all_tabs.extend(names)
    return all_tabs

def get_sub_tabs(subdir_name):
    """Get tabs from sub-files in pages subdirectory."""
    sub_path = pathlib.Path('pages') / subdir_name
    if not sub_path.exists():
        return {}
    result = {}
    for f in sorted(sub_path.glob('*.py')):
        content = f.read_text(encoding='utf-8', errors='ignore')
        lines = content.count('\n')
        tab_calls = re.findall(r'st\.tabs\(\s*\[([^\]]+)\]', content)
        tabs = []
        for call in tab_calls:
            names = re.findall(r'["\']([\w\s\U00010000-\U0010ffff\u0080-\uFFFF/:,\-\.\(\)]+)["\']', call)
            tabs.extend(names)
        result[f.name] = (lines, tabs)
    return result

for fname, subdir in sub_dirs.items():
    fpath = pages_dir / fname
    if not fpath.exists():
        print(f"\n{'='*60}\n{fname}: NOT FOUND")
        continue
    content = fpath.read_text(encoding='utf-8', errors='ignore')
    lines = content.count('\n')
    main_tabs = get_tabs(fpath)
    print(f"\n{'='*60}")
    print(f"{fname} ({lines} lines)")
    print(f"  Main tabs: {main_tabs}")
    if subdir:
        sub = get_sub_tabs(subdir)
        for sfname, (slines, stabs) in sub.items():
            print(f"  [{sfname}] ({slines}L) -> {stabs}")
