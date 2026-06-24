# 5. Inject vao HTML
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace UPDATED_AT - tim theo pattern khong phu thuoc noi dung cu
import re
html = re.sub(
    r'const UPDATED_AT = "[^"]*";',
    'const UPDATED_AT = "' + updated_at + '";',
    html
)

# Replace RAW_DATA - tim theo pattern
html = re.sub(
    r'const RAW_DATA = \[.*?\];',
    'const RAW_DATA = ' + raw_json + ';',
    html,
    flags=re.DOTALL
)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Done:", updated_at, "| Total USD:", df.Thanhtien.sum())
