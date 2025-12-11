import pandas as pd
import requests
import datetime
from io import BytesIO

# --- Excel Data Loading ---

def load_budget_data(file_or_path):
    try:
        # Load Excel
        # pd.read_excel accepts both string paths and file-like objects
        df = pd.read_excel(file_or_path, sheet_name="Hoja1")
        
        # Rename columns
        if "KILOS" in df.columns:
            df = df.rename(columns={"KILOS": "PPTO"})
        
        # Remove 'Code' column if exists
        if "Code" in df.columns:
            df = df.drop(columns=["Code"])
            
        # --- VALIDATION ---
        required_columns = ["PPTO", "ESTADO", "PRODUCTO", "VARIEDAD", "MANEJO"]
        missing_cols = [col for col in required_columns if col not in df.columns]
        
        # Check for at least one date column
        if "FECHAS MOD" not in df.columns and "MES" not in df.columns:
            missing_cols.append("FECHAS MOD or MES")
            
        if missing_cols:
            raise ValueError(f"El archivo no tiene la estructura correcta. Faltan las columnas: {', '.join(missing_cols)}")
            
        return df
    except FileNotFoundError:
        print(f"File not found: {file_or_path}")
        return pd.DataFrame()
    except ValueError as ve:
        # Re-raise validation errors to be caught by UI
        raise ve
    except Exception as e:
        print(f"Error loading budget data: {e}")
        raise ValueError(f"Error al leer el archivo Excel: {e}")

def load_dates_data(file_or_path):
    try:
        df = pd.read_excel(file_or_path, sheet_name="Fechas")
        
        # Filter nulls (Power Query logic approximation)
        df = df.dropna(how='all')
        
        # --- VALIDATION ---
        required_columns = ["Fecha", "Semana"]
        missing_cols = [col for col in required_columns if col not in df.columns]
        
        if missing_cols:
            raise ValueError(f"El archivo de Fechas no tiene la estructura correcta. Faltan las columnas: {', '.join(missing_cols)}")
        
        # Promote headers if needed (Pandas usually handles this, assuming first row is header)
        # Ensure types
        if "Fecha" in df.columns:
            df["Fecha"] = pd.to_datetime(df["Fecha"])
        if "Semana" in df.columns:
            df["Semana"] = pd.to_numeric(df["Semana"], errors='coerce')
            
        return df
    except FileNotFoundError:
        print(f"File not found: {file_or_path}")
        return pd.DataFrame()
    except ValueError as ve:
        raise ve
    except Exception as e:
        print(f"Error loading dates data: {e}")
        raise ValueError(f"Error al leer el archivo de Fechas: {e}")

def load_budget_2026_data(file_or_path):
    try:
        df = pd.read_excel(file_or_path, sheet_name="Hoja1")
        
        # --- VALIDATION ---
        # Types: Producto, Manejo, Tipo PPTO (text), Mes (date), Kilos (number)
        required_columns = ["Mes", "Producto", "Manejo", "Kilos"] # Based on user description and common sense
        # Note: User mentioned "PPTO's 2026.xlsx" has "Mes", "Producto", "Manejo", "Kilos" implicitly or explicitly.
        # Let's check the actual file content if possible, but for now strict validation on these seems safe based on previous context or user prompt.
        # Wait, looking at previous `load_budget_2026_data` implementation, it only checked for "Mes".
        # Let's be slightly more lenient but still check for "Mes" as it's critical.
        
        if "Mes" not in df.columns:
             raise ValueError("El archivo de Presupuesto Futuro debe tener la columna 'Mes'.")
             
        if "Mes" in df.columns:
            df["Mes"] = pd.to_datetime(df["Mes"])
        return df
    except FileNotFoundError:
        print(f"File not found: {file_or_path}")
        return pd.DataFrame()
    except ValueError as ve:
        raise ve
    except Exception as e:
        print(f"Error loading budget 2026 data: {e}")
        raise ValueError(f"Error al leer el archivo de Presupuesto Futuro: {e}")

# --- Odoo Data Fetching ---

# Token Library: Maps Token -> (Category Index, Standard Value)
# Categories: 0=Fruit, 1=Variety, 2=Labeling, 3=Quality, 4=Condition
TOKEN_LIBRARY = {
    # FRUITS (Index 0)
    "AR": (0, "ARANDANO"), "ARANDANO": (0, "ARANDANO"),
    "FB": (0, "FRAMBUESA"), "FRAMBUESA": (0, "FRAMBUESA"),
    "MO": (0, "MORA"), "MORA": (0, "MORA"),
    "FR": (0, "FRUTILLA"), "FT": (0, "FRUTILLA"), "FRUTILLA": (0, "FRUTILLA"),
    "CR": (0, "CEREZA"), "CEREZA": (0, "CEREZA"),
    "MIX": (0, "MORA"), "MIXED": (0, "MORA"), "BERRIES": (0, "MORA"), # Mix Berries -> MORA
    
    # VARIETIES (Index 1)
    "HB": (1, "HIGHBUSH"), "HIGHBUSH": (1, "HIGHBUSH"),
    "MK": (1, "MEEKER"), "MEEKER": (1, "MEEKER"),
    "WF": (1, "WAKEFIELD"), "WILD": (1, "WAKEFIELD"),
    "DUKE": (1, "DUKE"),
    "HE": (1, "HERITAGE"), "HERITAGE": (1, "HERITAGE"),
    "RY": (1, "REGINA"), "REGINA": (1, "REGINA"),
    "S/V": (1, "SIN VARIEDAD"), "SV": (1, "SIN VARIEDAD"), "SIN": (1, "SIN VARIEDAD"),
    "AB": (1, "ALBION"), "ALBION": (1, "ALBION"),
    "SLICE": (1, "SLICE"), # New Slice as Variety
    
    # LABELING (Index 2)
    "CONV": (2, "CONVENCIONAL"), "CONVENCIONAL": (2, "CONVENCIONAL"),
    "ORG": (2, "ORGANICO"), "ORGANICO": (2, "ORGANICO"),
    
    # QUALITY (Index 3)
    "IQF": (3, "IQF"),
    "BLOCK": (3, "BLOCK"),
    "AA": (3, "AA"),       # New AA
    "S/C": (3, "SIN CALIBRE"), # New S/C
    "<25MM": (3, "<25MM"),     # New <25MM
    
    # CONDITION (Index 4)
    "FRESCO": (4, "FRESCO"),
    "CONGELADO": (4, "CONGELADO"),
    "BANDEJA": (4, "CONGELADO"), # Heuristic: If in tray, usually frozen/processed? Or maybe just packaging.
    "PSP": (4, "CONGELADO"),     # Heuristic: PSP usually implies processed/frozen packaging
}

# Legacy Mapping for specific codes that don't follow the rule or need override
LEGACY_MAPPING = {
    "100105": "MORA_SIN VARIEDAD_CONVENCIONAL_IQF_CONGELADO", # Creative Gourmet Mixed Berries -> MORA
    "400007": "ARANDANO_HIGHBUSH_ORGANICO_IQF_FRESCO",
    "400011": "ARANDANO_HIGHBUSH_CONVENCIONAL_BLOCK_FRESCO",
    "400003": "ARANDANO_HIGHBUSH_CONVENCIONAL_IQF_FRESCO",
    "400001": "FRAMBUESA_MEEKER_CONVENCIONAL_IQF_FRESCO",
    "400025": "FRAMBUESA_WAKEFIELD_ORGANICO_IQF_FRESCO",
    "400029": "MORA_SIN VARIEDAD_CONVENCIONAL_IQF_FRESCO",
    "400058": "ARANDANO_DUKE_ORGANICO_IQF_FRESCO",
    "400002": "FRAMBUESA_HERITAGE_CONVENCIONAL_IQF_FRESCO",
    "400005": "FRAMBUESA_MEEKER_ORGANICO_IQF_FRESCO",
    "400027": "FRAMBUESA_WAKEFIELD_CONVENCIONAL_IQF_FRESCO",
    "400057": "ARANDANO_DUKE_CONVENCIONAL_IQF_FRESCO",
    "200050": "MORA_SIN VARIEDAD_CONVENCIONAL_IQF_CONGELADO",
    "200071": "MORA_SIN VARIEDAD_CONVENCIONAL_IQF_CONGELADO",
    "400004": "ARANDANO_REGINA_CONVENCIONAL_IQF_FRESCO",

    "400008": "ARANDANO_REGINA_ORGANICO_IQF_FRESCO",
    "400060": "ARANDANO_DUKE_ORGANICO_BLOCK_FRESCO",
    "400015": "ARANDANO_HIGHBUSH_ORGANICO_BLOCK_FRESCO",
    # "100105": "MORA_SIN VARIEDAD_CONVENCIONAL_IQF_CONGELADO", # Duplicate removed
    "400006": "FRAMBUESA_HERITAGE_ORGANICO_IQF_FRESCO",
    "400056": "MORA_SIN VARIEDAD_ORGANICO_IQF_FRESCO",
    "400061": "FRUTILLA_SIN VARIEDAD_ORGANICO_IQF_FRESCO",
    "100044": "FRUTILLA_SIN VARIEDAD_CONVENCIONAL_IQF_CONGELADO",
    "100074": "MORA_SIN VARIEDAD_ORGANICO_IQF_CONGELADO",
    "200034": "FRAMBUESA_HERITAGE_ORGANICO_IQF_CONGELADO",
    "200036": "ARANDANO_REGINA_ORGANICO_IQF_CONGELADO",
    "100078": "FRAMBUESA_HERITAGE_ORGANICO_IQF_CONGELADO",
    "100119": "MORA_SIN VARIEDAD_ORGANICO_IQF_CONGELADO",
    "900000": "CEREZA_SIN VARIEDAD_CONVENCIONAL_IQF_CONGELADO",
    "100005": "ARANDANO_HIGHBUSH_ORGANICO_IQF_CONGELADO",
    "100133": "FRAMBUESA_HERITAGE_CONVENCIONAL_IQF_CONGELADO",
    "100073": "FRUTILLA_SIN VARIEDAD_ORGANICO_IQF_CONGELADO",
    "100130": "FRAMBUESA_SIN VARIEDAD_ORGANICO_IQF_CONGELADO",
    "100001": "ARANDANO_HIGHBUSH_CONVENCIONAL_IQF_CONGELADO",
    "100137": "FRAMBUESA_SIN VARIEDAD_ORGANICO_IQF_CONGELADO",
    "100125": "CEREZA_SIN VARIEDAD_CONVENCIONAL_IQF_CONGELADO",
    "100118": "MORA_SIN VARIEDAD_ORGANICO_IQF_CONGELADO",
    "100117": "ARANDANO_REGINA_ORGANICO_IQF_CONGELADO",
    "100121": "FRUTILLA_SIN VARIEDAD_CONVENCIONAL_IQF_CONGELADO",
    "100126": "FRUTILLA_SIN VARIEDAD_CONVENCIONAL_IQF_CONGELADO",
    "100127": "FRUTILLA_SIN VARIEDAD_CONVENCIONAL_IQF_CONGELADO",
    "100007": "ARANDANO_REGINA_ORGANICO_IQF_CONGELADO",
    "100003": "ARANDANO_REGINA_CONVENCIONAL_IQF_CONGELADO",
    "100072": "FRAMBUESA_HERITAGE_CONVENCIONAL_IQF_CONGELADO",
}

def get_purchase_orders(client):
    """
    Fetches purchase orders from Odoo and returns a pandas DataFrame.
    """
    # Define fields to fetch
    po_fields = ['name', 'partner_id', 'date_order', 'date_approve', 'amount_total', 'currency_id', 'state', 'date_planned', 'picking_type_id']
    po_line_fields = ['order_id', 'product_id', 'name', 'product_qty', 'price_unit', 'price_subtotal', 'qty_received', 'date_planned']
    product_fields = ['default_code', 'name', 'categ_id', 'uom_id', 'x_studio_selection_field_7qfiv']
    category_fields = ['name', 'complete_name', 'parent_id']

    # Fetch Purchase Orders (limit by date to optimize if needed, but user wants all history)
    # For now, fetch all confirmed/done POs or filter later
    # Odoo domain filter
    domain = [('state', 'in', ['purchase', 'done'])]
    
    pos = client.search_read('purchase.order', domain, po_fields, context={'active_test': False})
    if not pos:
        return pd.DataFrame()
        
    po_ids = [po['id'] for po in pos]
    
    # Fetch PO Lines
    lines = client.search_read('purchase.order.line', [('order_id', 'in', po_ids)], po_line_fields, context={'active_test': False})
    
    # Fetch Products
    product_ids = list(set([line['product_id'][0] for line in lines if line['product_id']]))
    products = client.search_read('product.product', [('id', 'in', product_ids)], product_fields, context={'active_test': False})
    
    # Fetch Categories
    categ_ids = list(set([p['categ_id'][0] for p in products if p['categ_id']]))
    categories = client.search_read('product.category', [('id', 'in', categ_ids)], category_fields, context={'active_test': False})
    
    # Create DataFrames
    df_po = pd.DataFrame(pos)
    df_lines = pd.DataFrame(lines)
    df_products = pd.DataFrame(products)
    df_cats = pd.DataFrame(categories)
    
    # Helper to extract ID from Many2one
    def get_id(val):
        return val[0] if isinstance(val, (list, tuple)) and len(val) > 0 else val

    # Prepare Lines for Merge
    if df_lines.empty:
        return pd.DataFrame()
        
    df_lines['order_id_val'] = df_lines['order_id'].apply(get_id)
    df_lines['product_id_val'] = df_lines['product_id'].apply(get_id)
    
    # Merge Data
    # 1. Merge Lines with POs
    df = pd.merge(df_lines, df_po, left_on='order_id_val', right_on='id', suffixes=('', '_po'))
    
    # 2. Merge with Products
    df = pd.merge(df, df_products, left_on='product_id_val', right_on='id', suffixes=('', '_prod'))
    
    # 3. Merge with Categories
    if not df_cats.empty:
        df['categ_id_val'] = df['categ_id'].apply(get_id)
        df = pd.merge(df, df_cats, left_on='categ_id_val', right_on='id', suffixes=('', '_cat'))
        
    # --- Timezone Conversion (UTC -> America/Santiago) ---
    # Odoo stores in UTC. We need to convert to Chile time for accurate daily filtering.
    for col in ['date_planned', 'date_order', 'date_approve']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
            # Assuming data from Odoo is naive UTC (which it usually is via API)
            # We localize to UTC, convert to Santiago, then remove tz info to keep it naive but local
            try:
                df[col] = df[col].dt.tz_localize('UTC').dt.tz_convert('America/Santiago').dt.tz_localize(None)
            except Exception as e:
                # If already tz-aware or error, fallback (maybe log it)
                pass

    # Filter by Product Category "Producto" (matches Odoo Analysis)
    if 'complete_name' in df.columns:
        # Use complete_name from product.category
        # User requested "Producto" and "PRODUCTO"
        # Also include "Materia Prima" as new products might be there
        df = df[df['complete_name'].str.contains("Producto|PRODUCTO|Materia Prima|MATERIA PRIMA", case=False, na=False)]
    elif 'categ_name' in df.columns:
        # Fallback to leaf name if complete_name fetch failed
        df = df[df['categ_name'].str.contains("Producto|PRODUCTO|Materia Prima|MATERIA PRIMA", case=False, na=False)]
    
    def parse_product_code(row):
        code = str(row.get('default_code', '')).strip()
        name_prod = str(row.get('name_prod', '')).strip()
        desc = str(row.get('name', '')).strip() # PO Line Description
        
        # Handle -24 suffix (Year 2024)
        if code.endswith('-24'):
            code = code[:-3]
            
        # 1. Legacy Mapping / Overrides (Highest Priority)
        if code in LEGACY_MAPPING: return LEGACY_MAPPING[code]
            
        # Helper to clean text
        def clean_text(text):
            if ']' in text:
                text = text.split(']', 1)[1].strip()
            # Replace common separators with spaces to tokenize easily
            return text.replace('_', ' ').replace('.', ' ').replace('-', ' ')

        # Prioritize Desc > Name > Code
        # The PO Line Description is usually the most accurate source of truth for what was actually ordered.
        search_texts = [clean_text(desc), clean_text(name_prod), clean_text(code)]
        
        # Initialize result: [Fruit, Variety, Labeling, Quality, Condition]
        # Default to "OTRO"
        result = ["OTRO", "OTRO", "OTRO", "OTRO", "OTRO"]
        
        found_any = False
        
        for text in search_texts:
            if not text: continue
            
            # Clean text: replace punctuation with space to handle "Conv." or "Bandeja-2024"
            clean_text = text.upper().replace('.', ' ').replace('-', ' ').replace(',', ' ')
            tokens = clean_text.split()
            
            # Scan tokens
            for token in tokens:
                if token in TOKEN_LIBRARY:
                    idx, val = TOKEN_LIBRARY[token]
                    # Only overwrite if currently OTRO (first match wins? or last? usually first is better)
                    if result[idx] == "OTRO":
                        result[idx] = val
                        found_any = True
        
        # Post-Processing / Defaults
        
        # 1. Default Variety if Product is known but Variety is OTRO
        if result[0] != "OTRO" and result[1] == "OTRO":
            result[1] = "SIN VARIEDAD"
            
        # 2. Default Condition if Product is known but Condition is OTRO
        if result[0] != "OTRO" and result[4] == "OTRO":
            result[4] = "CONGELADO" # Default to Frozen for this business
            
        # 3. Default Quality if Product is known but Quality is OTRO
        if result[0] != "OTRO" and result[3] == "OTRO":
             result[3] = "ESTANDAR"
        
        # If Condition is OTRO (handled above now, but keep fallback logic just in case)
        if result[4] == "OTRO":
            if result[3] in ["IQF", "BLOCK"]:
                result[4] = "CONGELADO"
            elif result[3] == "FRESCO": 
                result[4] = "FRESCO"
        
        if found_any:
             return "_".join(result)

        # Fallback: Legacy Mapping
        if code in LEGACY_MAPPING: return LEGACY_MAPPING[code]
        if name_prod in LEGACY_MAPPING: return LEGACY_MAPPING[name_prod]
        if desc in LEGACY_MAPPING: return LEGACY_MAPPING[desc]
        if len(code) >= 6 and code[:6] in LEGACY_MAPPING: return LEGACY_MAPPING[code[:6]]
            
        return "OTRO_OTRO_OTRO_OTRO_OTRO"
    
    df['parsed_code'] = df.apply(parse_product_code, axis=1)
    
    # Split parsed_code
    split_data = df['parsed_code'].str.split('_', expand=True)
    
    # Ensure we have 5 columns
    for i in range(5):
        if i not in split_data.columns:
            split_data[i] = "OTRO"
            
    df['product'] = split_data[0]
    df['variety'] = split_data[1]
    df['labeling'] = split_data[2]
    df['quality'] = split_data[3]
    df['condition'] = split_data[4]
    
    # Drop raw Many2one columns that might cause PyArrow issues (lists)
    # Also drop other intermediate columns if not needed
    # KEEP default_code and name_prod for debugging/display
    cols_to_drop = ['order_id', 'product_id', 'order_id_val', 'product_id_val', 'currency_id', 'parsed_code']
    
    # Process currency_id before dropping if we want to keep the info
    if 'currency_id' in df.columns:
        df['currency_name'] = df['currency_id'].apply(lambda x: x[1] if isinstance(x, (list, tuple)) and len(x) > 1 else str(x))
    
    df = df.drop(columns=cols_to_drop, errors='ignore')
    
    return df

def get_purchase_report_data(client, date_range=None):
    """
    Fetches aggregated data from purchase.report.
    Filters by category 'Producto' and optional date range.
    Returns the total quantity received.
    """
    domain = [('category_id', 'ilike', 'Producto')]
    
    if date_range and len(date_range) == 2:
        start_date = date_range[0].strftime('%Y-%m-%d')
        end_date = date_range[1].strftime('%Y-%m-%d')
        # purchase.report usually has date_order or date_approve. 
        # Let's use date_order as it's common for analysis.
        domain.append(('date_order', '>=', start_date))
        domain.append(('date_order', '<=', end_date))
        
    fields = ['qty_received']
    
    # We can use read_group for aggregation if we want to be efficient, 
    # but get_dataframe uses search_read which returns records.
    # Since purchase.report is a view, search_read returns the aggregated lines present in the view.
    # However, to get a single total, we might need to sum them up in Python 
    # or use read_group if the connector supported it easily.
    # Let's stick to get_dataframe and sum in Python as per current pattern.
    
    df = client.get_dataframe('purchase.report', domain, fields)
    
    if df.empty:
        return 0.0
        
    return df['qty_received'].sum()

def get_currencies(client):
    domain = [('active', '=', True)]
    fields = ['name', 'symbol', 'rate', 'active']
    return client.get_dataframe('res.currency', domain, fields)

# --- External API ---

def get_central_bank_data():
    url = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
    params = {
        "user": "fhorst@riofuturo.cl",
        "pass": "PowerBi2025",
        "firstdate": "2024-08-01",
        "lastdate": "2025-12-31",
        "timeseries": "F073.TCO.PRE.Z.D",
        "function": "GetSeries"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Parse logic
        if 'Series' in data and 'Obs' in data['Series']:
            obs = data['Series']['Obs']
            df = pd.DataFrame(obs)
            # Columns: indexDateString, value, statusCode
            df['value'] = df['value'].astype(str).str.replace(',', '.').astype(float)
            df['indexDateString'] = pd.to_datetime(df['indexDateString'], format='%d-%m-%Y')
            return df
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching Central Bank data: {e}")
        return pd.DataFrame()

# --- Static Data ---

def get_pricing_data():
    data = [
        {"ESTADO": "FRESCO", "FRUTA": "ARANDANO", "MANEJO": "CONVENCIONAL", "$ PPTO": "2.8"},
        {"ESTADO": "FRESCO", "FRUTA": "ARANDANO", "MANEJO": "ORGANICO", "$ PPTO": "2.9"},
        {"ESTADO": "FRESCO", "FRUTA": "FRAMBUESA", "MANEJO": "CONVENCIONAL", "$ PPTO": "4"},
        {"ESTADO": "FRESCO", "FRUTA": "FRAMBUESA", "MANEJO": "ORGANICO", "$ PPTO": "3.5"},
        {"ESTADO": "FRESCO", "FRUTA": "MORA", "MANEJO": "CONVENCIONAL", "$ PPTO": "1.5"},
    ]
    df = pd.DataFrame(data)
    df['$ PPTO'] = pd.to_numeric(df['$ PPTO'])
    return df

def get_static_data():
    variety_data = {
        "Variety_short": ["AR", "FB", "MO", "FR", "CR"],
        "Variety_long": ["ARANDANO", "FRAMBUESA", "MORA", "FRUTILLA", "CEREZA"]
    }
    
    state_data = {"State": ["FRESCO", "CONGELADO"]}
    
    type_data = {
        "type_short": ["CONV", "ORG"],
        "type_long": ["CONVENCIONAL", "ORGANICO"]
    }
    
    # Weeks - basic 1-52 generation or hardcoded list if specific
    weeks_data = {"Semana": list(range(1, 54))}
    
    product_data = {
        "Product_short": ["HB", "MK", "WF", "DUKE", "HE", "RY", "S/V", "AB"],
        "Product_long": ["HIGHBUSH", "MEEKER", "WILD FLAVOUR", "DUKE", "HERITAGE", "REGINA", "SIN VARIEDAD", "ALBION"]
    }
    
    presupuesto_data = {"Presupuesto": ["Original", "Rev.2", "Rev.3"]}
    
    return {
        "Variety": pd.DataFrame(variety_data),
        "State": pd.DataFrame(state_data),
        "Type": pd.DataFrame(type_data),
        "Weeks": pd.DataFrame(weeks_data),
        "Product": pd.DataFrame(product_data),
        "Presupuesto": pd.DataFrame(presupuesto_data)
    }
