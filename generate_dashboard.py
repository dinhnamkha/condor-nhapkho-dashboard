#!/usr/bin/env python3
# generate_dashboard.py — Condor Nhập Kho Dashboard (USD)
import gspread, json, os
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
from datetime import datetime

# ── 1. Đọc credentials từ GitHub Secret ──
creds_info = json.loads(os.environ['GSHEET_CREDENTIALS'])
creds = Credentials.from_service_account_info(
    creds_info,
    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
)
client = gspread.authorize(creds)

# ── 2. Đọc Google Sheets ──
SHEET_ID = '1VjLAd980HSDDMghANst8UtT09H5bH3pa_lhSm6054uY'
ws     = client.open_by_key(SHEET_ID).get_worksheet(0)
df_raw = pd.DataFrame(ws.get_all_records())

# ── 3. Làm sạch (USD) ──
df = df_raw[
    df_raw['Ngay'].notna() &
    (df_raw['Ngay'] != '') &
    (df_raw['Ngay'] != 'Ngay')
].copy()
df['Ngay'] = pd.to_datetime(df['Ngay'], format='%d/%m/%Y', errors='coerce')
df['Dongia'] = pd.to_numeric(
    df['Dongia'].astype(str).str.replace(',', '.', regex=False),
    errors='coerce').fillna(0.0)
df['Thanhtien'] = pd.to_numeric(
    df['Thanhtien'].astype(str)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False),
    errors='coerce').fillna(0.0)
df['Soluong'] = pd.to_numeric(
    df['Soluong'].astype(str).str.replace('.', '', regex=False),
    errors='coerce').fillna(0)

# ── 4. Chuẩn bị JSON cho dashboard ──
def serialize(obj):
    if hasattr(obj, 'strftime'): return obj.strftime('%d/%m/%Y')
    if isinstance(obj, (np.integer,)): return int(obj)
    if isinstance(obj, (np.floating,)): return float(obj)
    return str(obj)

raw_records = df.sort_values('Ngay').rename(columns={
    'Ngay': 'ngay', 'To': 'to', 'Matp': 'matp',
    'Tentp': 'tentp', 'Soluong': 'soluong',
    'Dongia': 'dongia', 'Thanhtien': 'thanhtien'
})[['ngay','to','matp','tentp','soluong','dongia','thanhtien']].to_dict('records')

raw_json   = json.dumps(raw_records, default=serialize)
updated_at = datetime.now().strftime('%d/%m/%Y %H:%M')

# ── 5. Inject data vào HTML template ──
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace(
    'const UPDATED_AT = "24/06/2026 16:00 (dữ liệu mẫu)";',
    f'const UPDATED_AT = "{updated_at}";'
)
start = html.find('const RAW_DATA = [')
end   = html.find('];\n\n// ═══', start) + len('];\n\n// ═══')
html  = html[:start] + f'const RAW_DATA = {raw_json};\n\n// ═══' + html[end:]

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Done: {updated_at} | Total: ${df.Thanhtien.sum():,.2f} USD")
