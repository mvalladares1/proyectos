"""
Servicio de datos para el dashboard de Abastecimiento.
Incluye TOKEN_LIBRARY para parsing inteligente de códigos de producto.
"""
import pandas as pd
import requests
from io import BytesIO

# --- Excel Data Loading ---

def load_budget_data(file_or_path):
    try:
        df = pd.read_excel(file_or_path, sheet_name="Hoja1")
        if "KILOS" in df.columns:
            df = df.rename(columns={"KILOS": "PPTO"})
        if "Code" in df.columns:
            df = df.drop(columns=["Code"])
        required_columns = ["PPTO", "ESTADO", "PRODUCTO", "VARIEDAD", "MANEJO"]
        missing_cols = [col for col in required_columns if col not in df.columns]
        if "FECHAS MOD" not in df.columns and "MES" not in df.columns:
            missing_cols.append("FECHAS MOD or MES")
        if missing_cols:
            raise ValueError(f"El archivo no tiene la estructura correcta. Faltan las columnas: {', '.join(missing_cols)}")
        return df
    except FileNotFoundError:
        print(f"File not found: {file_or_path}")
        return pd.DataFrame()
    except ValueError as ve:
        raise ve
    except Exception as e:
        print(f"Error loading budget data: {e}")
        raise ValueError(f"Error al leer el archivo Excel: {e}")

def load_dates_data(file_or_path):
    try:
        df = pd.read_excel(file_or_path, sheet_name="Fechas")
        df = df.dropna(how='all')
        required_columns = ["Fecha", "Semana"]
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            raise ValueError(f"El archivo de Fechas no tiene la estructura correcta. Faltan las columnas: {', '.join(missing_cols)}")
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

# --- External API ---

def get_central_bank_data():
    """Obtiene datos del tipo de cambio desde el Banco Central de Chile."""
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
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'Series' in data and 'Obs' in data['Series']:
            obs = data['Series']['Obs']
            df = pd.DataFrame(obs)
            df['value'] = df['value'].astype(str).str.replace(',', '.').astype(float)
            df['indexDateString'] = pd.to_datetime(df['indexDateString'], format='%d-%m-%Y')
            return df
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching Central Bank data: {e}")
        return pd.DataFrame()

# --- Static Data ---

def get_pricing_data():
    """Retorna datos estáticos de precios presupuestados."""
    data = [
        {"ESTADO": "FRESCO", "FRUTA": "ARANDANO", "MANEJO": "CONVENCIONAL", "$ PPTO": 2.8},
        {"ESTADO": "FRESCO", "FRUTA": "ARANDANO", "MANEJO": "ORGANICO", "$ PPTO": 2.9},
        {"ESTADO": "FRESCO", "FRUTA": "FRAMBUESA", "MANEJO": "CONVENCIONAL", "$ PPTO": 4.0},
        {"ESTADO": "FRESCO", "FRUTA": "FRAMBUESA", "MANEJO": "ORGANICO", "$ PPTO": 3.5},
        {"ESTADO": "FRESCO", "FRUTA": "MORA", "MANEJO": "CONVENCIONAL", "$ PPTO": 1.5},
        {"ESTADO": "FRESCO", "FRUTA": "MORA", "MANEJO": "ORGANICO", "$ PPTO": 1.8},
        {"ESTADO": "FRESCO", "FRUTA": "FRUTILLA", "MANEJO": "CONVENCIONAL", "$ PPTO": 1.2},
        {"ESTADO": "FRESCO", "FRUTA": "FRUTILLA", "MANEJO": "ORGANICO", "$ PPTO": 1.5},
        {"ESTADO": "FRESCO", "FRUTA": "CEREZA", "MANEJO": "CONVENCIONAL", "$ PPTO": 3.0},
        {"ESTADO": "CONGELADO", "FRUTA": "ARANDANO", "MANEJO": "CONVENCIONAL", "$ PPTO": 2.5},
        {"ESTADO": "CONGELADO", "FRUTA": "ARANDANO", "MANEJO": "ORGANICO", "$ PPTO": 2.7},
        {"ESTADO": "CONGELADO", "FRUTA": "FRAMBUESA", "MANEJO": "CONVENCIONAL", "$ PPTO": 3.5},
        {"ESTADO": "CONGELADO", "FRUTA": "FRAMBUESA", "MANEJO": "ORGANICO", "$ PPTO": 3.2},
        {"ESTADO": "CONGELADO", "FRUTA": "MORA", "MANEJO": "CONVENCIONAL", "$ PPTO": 1.3},
        {"ESTADO": "CONGELADO", "FRUTA": "FRUTILLA", "MANEJO": "CONVENCIONAL", "$ PPTO": 1.0},
    ]
    return pd.DataFrame(data)

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
    "MIX": (0, "MORA"), "MIXED": (0, "MORA"), "BERRIES": (0, "MORA"),
    
    # VARIETIES (Index 1)
    "HB": (1, "HIGHBUSH"), "HIGHBUSH": (1, "HIGHBUSH"),
    "MK": (1, "MEEKER"), "MEEKER": (1, "MEEKER"),
    "WF": (1, "WAKEFIELD"), "WILD": (1, "WAKEFIELD"),
    "DUKE": (1, "DUKE"),
    "HE": (1, "HERITAGE"), "HERITAGE": (1, "HERITAGE"),
    "RY": (1, "REGINA"), "REGINA": (1, "REGINA"),
    "S/V": (1, "SIN VARIEDAD"), "SV": (1, "SIN VARIEDAD"), "SIN": (1, "SIN VARIEDAD"),
    "AB": (1, "ALBION"), "ALBION": (1, "ALBION"),
    "SLICE": (1, "SLICE"),
    
    # LABELING (Index 2)
    "CONV": (2, "CONVENCIONAL"), "CONVENCIONAL": (2, "CONVENCIONAL"),
    "ORG": (2, "ORGANICO"), "ORGANICO": (2, "ORGANICO"),
    
    # QUALITY (Index 3)
    "IQF": (3, "IQF"),
    "BLOCK": (3, "BLOCK"),
    "AA": (3, "AA"),
    "S/C": (3, "SIN CALIBRE"),
    "<25MM": (3, "<25MM"),
    
    # CONDITION (Index 4)
    "FRESCO": (4, "FRESCO"),
    "CONGELADO": (4, "CONGELADO"),
    "BANDEJA": (4, "CONGELADO"),
    "PSP": (4, "CONGELADO"),
}

# Legacy Mapping for specific codes that don't follow the rule
LEGACY_MAPPING = {
    "100105": "MORA_SIN VARIEDAD_CONVENCIONAL_IQF_CONGELADO",
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
    "100032": "FRAMBUESA_HERITAGE_ORGANICO_IQF_CONGELADO",
    # Códigos de bandeja
    "102122000": "FRAMBUESA_MEEKER_CONVENCIONAL_IQF_CONGELADO",
    "102121000": "FRAMBUESA_SIN VARIEDAD_CONVENCIONAL_IQF_CONGELADO",
    "101122000": "ARANDANO_HIGHBUSH_CONVENCIONAL_IQF_CONGELADO",
    "101222000": "ARANDANO_HIGHBUSH_ORGANICO_IQF_CONGELADO",
    "103122000": "FRUTILLA_ALBION_CONVENCIONAL_IQF_CONGELADO",
    "103222000": "FRUTILLA_ALBION_ORGANICO_IQF_CONGELADO",
}


def get_purchase_orders(client):
    """
    Fetches purchase orders from Odoo and returns a pandas DataFrame.
    Uses TOKEN_LIBRARY for intelligent product code parsing.
    """
    try:
        # Fetch POs
        po_fields = [
            'id', 'name', 'date_planned', 'currency_id', 'x_studio_categora_de_producto',
            'amount_tax', 'amount_total', 'amount_untaxed', 'invoice_status', 'receipt_status',
            'state', 'date_order', 'date_approve'
        ]
        pos = pd.DataFrame(client.search_read('purchase.order', [('state', 'in', ['purchase', 'done'])], fields=po_fields))

        if pos.empty:
            return pd.DataFrame()

        # Normalize category field
        if 'x_studio_categora_de_producto' in pos.columns:
            pos['x_studio_categora_de_producto'] = pos['x_studio_categora_de_producto'].apply(lambda x: str(x) if x and x is not False else "")

        # Fill date_planned
        if 'date_planned' in pos.columns and 'date_order' in pos.columns:
            pos['date_planned'] = pos['date_planned'].replace({False: None}).fillna(pos['date_order'])

        po_ids = pos['id'].tolist()
        if not po_ids:
            return pd.DataFrame()

        # Fetch lines
        line_fields = ['id', 'order_id', 'product_id', 'price_unit', 'price_total', 'price_subtotal', 'product_qty', 'qty_invoiced', 'qty_received', 'name']
        lines = pd.DataFrame(client.search_read('purchase.order.line', [('order_id', 'in', po_ids)], fields=line_fields))
        if lines.empty:
            return pd.DataFrame()

        # Fetch products
        product_ids = [x[0] if isinstance(x, (list, tuple)) and len(x) > 0 else x for x in lines['product_id'].tolist()]
        product_ids = [p for p in product_ids if p is not None]
        product_fields = ['id', 'default_code', 'name', 'x_studio_selection_field_7qfiv', 'categ_id']
        products = pd.DataFrame(client.search_read('product.product', [('id', 'in', product_ids)], fields=product_fields)) if product_ids else pd.DataFrame()

        # Fetch categories
        if not products.empty and 'categ_id' in products.columns:
            products['categ_join_id'] = products['categ_id'].apply(lambda x: x[0] if isinstance(x, (list, tuple)) and len(x) > 0 else None)
            cat_ids = products['categ_join_id'].dropna().unique().tolist()
            if cat_ids:
                categories = pd.DataFrame(client.search_read('product.category', [('id', 'in', cat_ids)], fields=['id', 'complete_name']))
                products = pd.merge(products, categories, left_on='categ_join_id', right_on='id', how='left', suffixes=('', '_cat'))

        # Prepare lines for merge
        lines['order_id_val'] = lines['order_id'].apply(lambda x: x[0] if isinstance(x, (list, tuple)) else x)
        lines['product_id_val'] = lines['product_id'].apply(lambda x: x[0] if isinstance(x, (list, tuple)) else x)

        df = pd.merge(lines, pos, left_on='order_id_val', right_on='id', suffixes=('_line', '_po'))
        if not products.empty:
            df = pd.merge(df, products, left_on='product_id_val', right_on='id', suffixes=('', '_prod'))

        # Filter received
        if 'qty_received' in df.columns:
            df = df[df['qty_received'] != 0]

        # Filter by category containing 'Producto'
        if 'complete_name' in df.columns:
            df = df[df['complete_name'].str.contains('Producto|PRODUCTO|Materia Prima|MATERIA PRIMA', case=False, na=False)]

        # Parse product codes using TOKEN_LIBRARY
        def parse_product_code(row):
            code = str(row.get('default_code', '')).strip()
            name_prod = str(row.get('name_prod', row.get('name', ''))).strip()
            desc = str(row.get('name_line', row.get('name', ''))).strip()
            
            # Handle -24 suffix (Year 2024)
            if code.endswith('-24'):
                code = code[:-3]
                
            # 1. Legacy Mapping (Highest Priority)
            if code in LEGACY_MAPPING:
                return LEGACY_MAPPING[code]
            
            # Helper to clean text
            def clean_text(text):
                if ']' in text:
                    text = text.split(']', 1)[1].strip()
                return text.replace('_', ' ').replace('.', ' ').replace('-', ' ')

            search_texts = [clean_text(desc), clean_text(name_prod), clean_text(code)]
            
            # Initialize result: [Fruit, Variety, Labeling, Quality, Condition]
            result = ["OTRO", "OTRO", "OTRO", "OTRO", "OTRO"]
            
            found_any = False
            
            for text in search_texts:
                if not text:
                    continue
                    
                clean = text.upper().replace('.', ' ').replace('-', ' ').replace(',', ' ')
                tokens = clean.split()
                
                for token in tokens:
                    if token in TOKEN_LIBRARY:
                        idx, val = TOKEN_LIBRARY[token]
                        if result[idx] == "OTRO":
                            result[idx] = val
                            found_any = True
            
            # Post-Processing / Defaults
            if result[0] != "OTRO" and result[1] == "OTRO":
                result[1] = "SIN VARIEDAD"
            if result[0] != "OTRO" and result[4] == "OTRO":
                result[4] = "CONGELADO"
            if result[0] != "OTRO" and result[3] == "OTRO":
                result[3] = "IQF"
                
            if found_any:
                return "_".join(result)
                
            return "OTRO_OTRO_OTRO_OTRO_OTRO"

        df['parsed_code'] = df.apply(parse_product_code, axis=1)
        
        split_data = df['parsed_code'].str.split('_', expand=True)
        for i in range(5):
            if i not in split_data.columns:
                split_data[i] = "OTRO"
                
        df['product'] = split_data[0]
        df['variety'] = split_data[1]
        df['labeling'] = split_data[2]
        df['quality'] = split_data[3]
        df['condition'] = split_data[4]

        cols_to_drop = ['order_id', 'product_id', 'order_id_val', 'product_id_val', 'parsed_code']
        df = df.drop(columns=cols_to_drop, errors='ignore')

        # Currency name cleanup
        if 'currency_id' in df.columns:
            df['currency_name'] = df['currency_id'].apply(lambda x: x[1] if isinstance(x, (list, tuple)) and len(x) > 1 else str(x))

        # Timezone conversion
        for col in ['date_planned', 'date_order', 'date_approve']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])
                try:
                    df[col] = df[col].dt.tz_localize('UTC').dt.tz_convert('America/Santiago').dt.tz_localize(None)
                except:
                    pass

        return df
    except Exception as e:
        print(f"Error in get_purchase_orders: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def get_purchase_report_data(client, date_range=None):
    """Fetches aggregated data from purchase.report."""
    domain = [('category_id', 'ilike', 'Producto')]
    if date_range and len(date_range) == 2:
        start_date = date_range[0].strftime('%Y-%m-%d')
        end_date = date_range[1].strftime('%Y-%m-%d')
        domain.append(('date_order', '>=', start_date))
        domain.append(('date_order', '<=', end_date))
    fields = ['qty_received']
    df = pd.DataFrame(client.search_read('purchase.report', domain, fields=fields))
    if df.empty:
        return 0.0
    return df['qty_received'].sum()


def get_currencies(client):
    """Fetches active currencies from Odoo."""
    domain = [('active', '=', True)]
    fields = ['name', 'symbol', 'rate', 'active']
    return pd.DataFrame(client.search_read('res.currency', domain, fields=fields))
