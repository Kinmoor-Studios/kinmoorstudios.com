# Social preview image (og.jpg, 1200 x 630): the hero in dark mode, still, without the speed panel, buttons, or moving lights.
# Usage, from the repo root: python3 _source/tools/local-server.py . 8766  (in another terminal), then: python3 _source/tools/og-image.py http://127.0.0.1:8766/ og.jpg
import sys, io
from playwright.sync_api import sync_playwright
from PIL import Image
url = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8766/'
out = sys.argv[2] if len(sys.argv) > 2 else 'og.jpg'
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1200, 'height': 630}, device_scale_factor=1, color_scheme='dark', reduced_motion='reduce', bypass_csp=True)
    pg.goto(url); pg.wait_for_timeout(2500)
    pg.add_style_tag(content='.readout,.hero .cta,.hero .btn,#contours-lights,.theme-toggle{visibility:hidden!important}')
    pg.wait_for_timeout(500)
    png = pg.screenshot()
    b.close()
Image.open(io.BytesIO(png)).convert('RGB').save(out, 'JPEG', quality=84, optimize=True, progressive=True)
print(out, 'written')
