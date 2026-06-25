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
df['Thanhtien'] = pd.to_numeric(
    df['Thanhtien'].astype(str)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False),
    errors='coerce').fillna(0.0)
df['Soluong'] = pd.to_numeric(
    df['Soluong'].astype(str).str.replace('.', '', regex=False),
    errors='coerce').fillna(0)
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
    'Tentp':'tentp','Soluong':'soluong',
    'Dongia':'dongia','Thanhtien':'thanhtien'
})[['ngay','to','matp','tentp','soluong','dongia','thanhtien']].to_dict('records')

raw_json   = json.dumps(raw_records, default=serialize)
ICT = timezone(timedelta(hours=7))
updated_at = datetime.now(ICT).strftime('%d/%m/%Y %H:%M')

# 5. Inject vao HTML
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace UPDATED_AT bang regex
html = re.sub(
    r'const UPDATED_AT = "[^"]*";',
    'const UPDATED_AT = "' + updated_at + '";',
    html
)

# Replace RAW_DATA bang string find (tranh loi regex voi Unicode)
start_marker = 'const RAW_DATA = ['
end_marker   = '];'
start_pos = html.find(start_marker)
end_pos   = html.find(end_marker, start_pos) + len(end_marker)
html = html[:start_pos] + 'const RAW_DATA = ' + raw_json + ';' + html[end_pos:]

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Done:", updated_at, "| Total USD:", df.Thanhtien.sum())
