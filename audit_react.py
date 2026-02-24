import pathlib, re

base = pathlib.Path('MIGRACION/src/features')

feature_dirs = sorted([d for d in base.iterdir() if d.is_dir()])

for fdir in feature_dirs:
    page_files = list(fdir.glob('*Page.tsx'))
    if not page_files:
        continue
    for pf in page_files:
        content = pf.read_text(encoding='utf-8', errors='ignore')
        lines = content.count('\n')
        # Find TabsTrigger values
        tab_values = re.findall(r'<TabsTrigger\s+value=["\']([^"\']+)["\']>([^<]+)<', content)
        # KPICards
        kpi_count = len(re.findall(r'<KPICard', content))
        # Charts
        charts = re.findall(r'<(BarChart|LineChart|PieChart|AreaChart)[^>]', content)
        # DataTables
        tables = len(re.findall(r'<DataTable', content))
        print(f"\n{'='*55}")
        print(f"{pf.name} ({lines}L) KPIs:{kpi_count} Charts:{len(charts)} Tables:{tables}")
        for val, label in tab_values:
            print(f"  tab [{val}]: {label.strip()}")
