import gspread, json, os, re
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

# 1. Credentials tu GitHub Secret
creds_info = json.loads(os.environ['GSHEET_CREDENTIALS'])
creds = Credentials.from_service_account_info(
    creds_info,
    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
)
client = gspread.authorize(creds)

# 2. Doc tab Data (chu D hoa)
SHEET_ID = '1VjLAd980HSDDMghANst8UtT09H5bH3pa_lhSm6054uY'
ws = client.open_by_key(SHEET_ID).worksheet('Data')
all_values = ws.get_all_values()
headers = all_values[0]
rows    = all_values[1:]
df      = pd.DataFrame(rows, columns=headers)

# 3. Lam sach
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

# 4. Serialize
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

raw_json   = json.dumps(raw_records, default=serialize, ensure_ascii=False)
ICT        = timezone(timedelta(hours=7))
updated_at = datetime.now(ICT).strftime('%d/%m/%Y %H:%M')

# 5. Inject vao HTML
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# --- Replace UPDATED_AT ---
html = re.sub(
    r'const UPDATED_AT = "[^"]*";',
    'const UPDATED_AT = "' + updated_at + '";',
    html
)

# --- Replace RAW_DATA ---
# Dung marker chinh xac: tu "const RAW_DATA = [" den "];\n\n// "
# De tranh khop sai voi ]; khac trong file
START = 'const RAW_DATA = ['
END   = '];\n\n// '

start_pos = html.find(START)
end_pos   = html.find(END, start_pos)

if start_pos == -1:
    print("ERROR: Khong tim thay marker 'const RAW_DATA = ['")
    exit(1)
if end_pos == -1:
    # Fallback: tim ]; gan nhat sau START
    end_pos = html.find('];', start_pos)
    html = html[:start_pos] + 'const RAW_DATA = ' + raw_json + ';' + html[end_pos+2:]
else:
    html = html[:start_pos] + 'const RAW_DATA = ' + raw_json + ';\n\n// ' + html[end_pos + len(END):]

print(f"RAW_DATA injected: {len(raw_records)} records")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Done: {updated_at} | Total USD: {df.Giathanh.sum():,.2f}")
