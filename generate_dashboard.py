import gspread, json, os
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
from datetime import datetime

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
df
