import pandas as pd
import requests
from io import BytesIO

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


def get_purchase_orders(client):
    """Fetch purchase orders and lines, merge and transform similar to original dashboard logic."""
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

        # Filter by category containing 'Producto' if available
        if 'complete_name' in df.columns:
            df = df[df['complete_name'].str.contains('Producto|PRODUCTO', case=False, na=False)]

        # Map codes to name_code_2 (use a reduced mapping to avoid very long duplication)
        def get_name_code_2(row):
            code = str(row.get('default_code', '')).strip()
            mapping = {
                "400007": "AR_HB_ORG_IQF_FRESCO",
                "400011": "AR_HB_CONV_BLOCK_FRESCO",
                "400003": "AR_HB_CONV_IQF_FRESCO",
                "400001": "FB_MK_CONV_IQF_FRESCO",
                "400025": "FB_WF_ORG_IQF_FRESCO",
                "400029": "MO_S/V_CONV_IQF_FRESCO",
                "400058": "AR_DUKE_ORG_IQF_FRESCO",
                "400002": "FB_HE_CONV_IQF_FRESCO",
                "400005": "FB_MK_ORG_IQF_FRESCO",
                "400027": "FB_WF_CONV_IQF_FRESCO",
                "400057": "AR_DUKE_CONV_IQF_FRESCO",
                "200050": "MO_S/V_CONV_IQF_CONGELADO",
                "200071": "MO_S/V_CONV_IQF_CONGELADO",
                "400004": "AR_RY_CONV_IQF_FRESCO",
                "100032": "FB_HE_ORG_IQF_CONGELADO",
                "400008": "AR_RY_ORG_IQF_FRESCO",
                "400060": "AR_DUKE_ORG_BLOCK_FRESCO",
                "400015": "AR_HB_ORG_BLOCK_FRESCO",
                "100105": "MO_S/V_CONV_IQF_CONGELADO",
                "400006": "FB_HE_ORG_IQF_FRESCO",
                "400056": "MO_S/V_ORG_IQF_FRESCO",
                "400061": "FR_S/V_ORG_IQF_FRESCO",
                "100044": "FR_S/V_CONV_IQF_CONGELADO",
                "100074": "MO_S/V_ORG_IQF_CONGELADO",
                "200034": "FB_HE_ORG_IQF_CONGELADO",
                "200036": "AR_RY_ORG_IQF_CONGELADO",
                "100078": "FB_HE_ORG_IQF_CONGELADO",
                "100119": "MO_S/V_ORG_IQF_CONGELADO",
                "900000": "CR_S/V_CONV_IQF_CONGELADO",
                "100005": "AR_HB_ORG_IQF_CONGELADO",
                "100133": "FB_HE_CONV_IQF_CONGELADO",
                "100073": "FR_S/V_ORG_IQF_CONGELADO",
                "100130": "FB_S/V_ORG_IQF_CONGELADO",
                "100001": "AR_HB_CONV_IQF_CONGELADO",
                "100137": "FB_S/V_ORG_IQF_CONGELADO",
                "100125": "CR_S/V_CONV_IQF_CONGELADO",
                "100118": "MO_S/V_ORG_IQF_CONGELADO",
                "100117": "AR_RY_ORG_IQF_CONGELADO",
                "100121": "FR_S/V_CONV_IQF_CONGELADO",
                "100126": "FR_S/V_CONV_IQF_CONGELADO",
                "100127": "FR_S/V_CONV_IQF_CONGELADO",
                "100007": "AR_RY_ORG_IQF_CONGELADO",
                "100003": "AR_RY_CONV_IQF_CONGELADO",
                "100072": "FB_HE_CONV_IQF_CONGELADO",
                # New Mappings (Text-based codes or Names)
                "FT AB Conv. IQF en Bandeja": "FR_AB_CONV_IQF_CONGELADO",
                "AR HB Conv. IQF en Bandeja": "AR_HB_CONV_IQF_CONGELADO",
                "FT AB Conv. IQF en Bandeja (copia)": "FR_AB_CONV_IQF_CONGELADO",
                "FT AB Org. IQF en Bandeja": "FR_AB_ORG_IQF_CONGELADO",
                "FB S/V Conv. IQF en Bandeja": "FB_S/V_CONV_IQF_CONGELADO",
                "AR HB Org. IQF en Bandeja": "AR_HB_ORG_IQF_CONGELADO",
                "FB MK Conv. IQF en Bandeja": "FB_MK_CONV_IQF_CONGELADO",
                # Numeric Codes from Odoo Screenshot
                "102122000": "FB_MK_CONV_IQF_CONGELADO",
                "102121000": "FB_S/V_CONV_IQF_CONGELADO",
                "101122000": "AR_HB_CONV_IQF_CONGELADO",
                "101222000": "AR_HB_ORG_IQF_CONGELADO",
                "103122000": "FR_AB_CONV_IQF_CONGELADO",
                "103222000": "FR_AB_ORG_IQF_CONGELADO"
            }
            if code in mapping:
                return mapping[code]
            # Fallback
            return "OTRO"

        df['name_code_2'] = df.apply(get_name_code_2, axis=1)

        split_data = df['name_code_2'].str.split('_', expand=True)
        for i in range(5):
            if i not in split_data.columns:
                split_data[i] = None
        df['product'] = split_data[0]
        df['variety'] = split_data[1]
        df['labeling'] = split_data[2]
        df['quality'] = split_data[3]
        df['condition'] = split_data[4]

        cols_to_drop = ['order_id', 'product_id', 'order_id_val', 'product_id_val']
        df = df.drop(columns=cols_to_drop, errors='ignore')

        # Currency name cleanup
        if 'currency_id' in df.columns:
            df['currency_name'] = df['currency_id'].apply(lambda x: x[1] if isinstance(x, (list, tuple)) and len(x) > 1 else str(x))

        return df
    except Exception as e:
        print(f"Error in get_purchase_orders: {e}")
        return pd.DataFrame()


def get_purchase_report_data(client, date_range=None):
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
    domain = [('active', '=', True)]
    fields = ['name', 'symbol', 'rate', 'active']
    return pd.DataFrame(client.search_read('res.currency', domain, fields=fields))
