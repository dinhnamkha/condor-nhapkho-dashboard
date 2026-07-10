import gspread, json, os, re
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

# 1. Credentials
creds_info = json.loads(os.environ['GSHEET_CREDENTIALS'])
creds = Credentials.from_service_account_info(
    creds_info,
    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
)
client = gspread.authorize(creds)
SHEET_ID = '1VjLAd980HSDDMghANst8UtT09H5bH3pa_lhSm6054uY'
sheet    = client.open_by_key(SHEET_ID)

# 2. Doc tab Data
ws_data    = sheet.worksheet('Data')
all_values = ws_data.get_all_values()
headers    = all_values[0]
df         = pd.DataFrame(all_values[1:], columns=headers)

# 3. Lam sach Data
df = df[df['Ngay'] != ''].copy()
df['Ngay'] = pd.to_datetime(df['Ngay'], format='%d/%m/%Y', errors='coerce')
df['Dongia'] = pd.to_numeric(
    df['Dongia'].astype(str).str.replace(',', '.', regex=False),
    errors='coerce').fillna(0.0)
df['Giathanh'] = pd.to_numeric(
    df['Giathanh'].astype(str)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False),
    errors='coerce').fillna(0.0)
df['Soluong'] = pd.to_numeric(
    df['Soluong'].astype(str).str.replace('.', '', regex=False),
    errors='coerce').fillna(0)
if 'Tenjp' not in df.columns:
    df['Tenjp'] = ''
else:
    df['Tenjp'] = df['Tenjp'].fillna('').astype(str).str.strip()
df['Thang'] = df['Ngay'].dt.to_period('M').astype(str)
df['Nam']   = df['Ngay'].dt.year

# 4. Doc tab Kehoach
# Columns: Matp, Tentp, Nhom, To, Soluong, Thangsx
try:
    ws_kh   = sheet.worksheet('Kehoach')
    kh_vals = ws_kh.get_all_values()
    kh_headers = kh_vals[0]
    df_kh   = pd.DataFrame(kh_vals[1:], columns=kh_headers)
    print(f"KH headers: {kh_headers}")
    print(f"KH total rows: {len(df_kh)}")
    df_kh   = df_kh[df_kh['Matp'] != ''].copy()
    print(f"KH rows after Matp filter: {len(df_kh)}")
    df_kh['Soluong'] = pd.to_numeric(
        df_kh['Soluong'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
        errors='coerce').fillna(0)
    # Thangsx co the la "2026-07" hoac "07/2026" hoac "7/2026"
    def parse_thang(t):
        t = str(t).strip()
        if '-' in t:
            return t[:7]  # yyyy-MM
        if '/' in t:
            parts = t.split('/')
            if len(parts[0]) == 4:
                return f"{parts[0]}-{parts[1].zfill(2)}"
            return f"{parts[1]}-{parts[0].zfill(2)}"
        return t
    # df_kh['Thangsx'] = df_kh['Thangsx'].apply(parse_thang)  # da doi sang Ngaynhapkho
    # Xu ly cot Tenjp
    if 'Tenjp' not in df_kh.columns:
        df_kh['Tenjp'] = ''
    else:
        df_kh['Tenjp'] = df_kh['Tenjp'].fillna('').astype(str).str.strip()
    # Xu ly Ngaynhapkho: chap nhan ca 'Ngaynhapkho' va 'Ngaynhapl' (ten rut gon)
    ngay_col = None
    for col in ['Ngaynhapkho', 'Ngaynhapl', 'NgayNhapKho', 'Ngay nhap kho']:
        if col in df_kh.columns:
            ngay_col = col
            break
    if ngay_col:
        print(f"Found date column: {ngay_col}")
        df_kh['Ngaynhapkho'] = pd.to_datetime(
            df_kh[ngay_col], format='%d/%m/%Y', errors='coerce'
        ).dt.strftime('%Y-%m-%d')
        df_kh['Ngaynhapkho'] = df_kh['Ngaynhapkho'].fillna('')
    else:
        print(f"WARNING: No date column found. Columns: {list(df_kh.columns)}")
        df_kh['Ngaynhapkho'] = ''
    kh_records = df_kh.rename(columns={
        'Matp':'matp','Tentp':'tentp','Tenjp':'tenjp','Nhom':'nhom',
        'To':'to','Soluong':'soluong_kh','Ngaynhapkho':'ngaynhapkho'
    })[['matp','tentp','tenjp','nhom','to','soluong_kh','ngaynhapkho']].to_dict('records')
    print(f"KH_DATA loaded: {len(kh_records)} records")
except Exception as e:
    kh_records = []
    import traceback
    print(f"WARNING: Kehoach sheet error: {e}")
    traceback.print_exc()

# 5. Serialize
def serialize(obj):
    if hasattr(obj, 'strftime'): return obj.strftime('%Y-%m-%d')
    if isinstance(obj, (np.integer,)): return int(obj)
    if isinstance(obj, (np.floating,)): return float(obj)
    return str(obj)

raw_records = df.sort_values('Ngay').rename(columns={
    'Ngay':'ngay','To':'to','Matp':'matp',
    'Tentp':'tentp','Tenjp':'tenjp','Soluong':'soluong',
    'Dongia':'dongia','Giathanh':'thanhtien'
})[['ngay','to','matp','tentp','tenjp','soluong','dongia','thanhtien']].to_dict('records')

raw_json = json.dumps(raw_records, default=serialize, ensure_ascii=False)
kh_json  = json.dumps(kh_records,  default=serialize, ensure_ascii=False)
ICT        = timezone(timedelta(hours=7))
updated_at = datetime.now(ICT).strftime('%d/%m/%Y %H:%M')

# 6. Inject vao HTML
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace UPDATED_AT
html = re.sub(
    r'const UPDATED_AT = "[^"]*";',
    'const UPDATED_AT = "' + updated_at + '";',
    html
)

# Replace RAW_DATA
START = 'const RAW_DATA = ['
END   = '];\n\n// '
start_pos = html.find(START)
end_pos   = html.find(END, start_pos)
if start_pos == -1:
    print("ERROR: marker 'const RAW_DATA = [' not found")
    exit(1)
if end_pos == -1:
    end_pos = html.find('];', start_pos)
    html = html[:start_pos] + 'const RAW_DATA = ' + raw_json + ';' + html[end_pos+2:]
else:
    html = html[:start_pos] + 'const RAW_DATA = ' + raw_json + ';\n\n// ' + html[end_pos + len(END):]

# Replace KH_DATA
KH_START = 'const KH_DATA = ['
KH_END   = '];\n\n// KH_END'
kh_start = html.find(KH_START)
kh_end   = html.find(KH_END, kh_start)
if kh_start == -1:
    print("WARNING: KH_DATA marker not found, skipping")
elif kh_end == -1:
    print("WARNING: KH_DATA end marker not found, skipping")
else:
    html = html[:kh_start] + 'const KH_DATA = ' + kh_json + ';\n\n// KH_END' + html[kh_end + len(KH_END):]

print(f"RAW_DATA injected: {len(raw_records)} records")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Done: {updated_at} | Total USD: {df.Giathanh.sum():,.2f}")
