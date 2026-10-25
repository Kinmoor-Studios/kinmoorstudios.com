# Builds the deployable site from _source, run from the repository root:
#   NODE_PATH=_source/tools/node_modules python3 _source/build.py
# For every language in _source/i18n: the home page and the privacy page (English at /, the others at /es/, /fr/, ...),
# plus 404.html (one page that speaks each language) and sitemap.xml. Each page is minified and gets a Content-Security-Policy
# built from hashes of its own inline code.
#
# Text: every run of text between tags, and every aria-label, title, placeholder, and alt, is looked up in the language's
# "text" table. The build stops if any is missing, so no English slips into a translation. The script's own phrases live in
# one table ("t") that replaces I18N_T in page.html.
#
# Fonts: tools/fonts.py renders each built page, records which characters each font actually draws, and writes subsets to
# fonts/<lang>/ with a manifest. This build reads the manifest, links those files with content hashes, and stops if a page
# uses a character its fonts don't have (run tools/fonts.py, then build again).
#
# Review: a language goes public when its file says "reviewed": true. Until then its pages exist (for reviewers) but are
# marked noindex and are left out of the switcher, the suggestion note, hreflang, and the sitemap.
import re, hashlib, base64, json, subprocess, os, sys
MIN = '_source/tools/min.js'
SITE = 'https://kinmoorstudios.com'
LANGS = os.environ.get('LANGS', 'en es fr de ja').split()  # LANGS=en builds English alone
D = {l: json.load(open(f'_source/i18n/{l}.json', encoding='utf-8')) for l in LANGS}
PUBLIC = [l for l in LANGS if D[l].get('reviewed')]
if os.environ.get('PUBLIC'): PUBLIC = os.environ['PUBLIC'].split(',')  # testing only: treat these languages as reviewed
EN = D['en']

def home(l): return '/' if l == 'en' else f'/{l}/'
def privacy(l): return '/privacy' if l == 'en' else f'/{l}/privacy'

# ---------- minify and secure ----------
def csp_for(html):
    """Content-Security-Policy that allows only this page's own inline code (by hash), its own fonts, and nothing else."""
    def h(text): return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"
    scripts = [h(m) for m in re.findall(r'<script(?: type="speculationrules")?>([\s\S]*?)</script>', html)]
    styles = [h(m) for m in re.findall(r'<style>([\s\S]*?)</style>', html)]
    return ("default-src 'none'; script-src " + ' '.join(scripts or ["'none'"]) + "; style-src " + ' '.join(styles or ["'none'"]) +
            "; img-src 'self' data:; font-src 'self'; manifest-src 'self'; worker-src blob:; connect-src 'self'"
            "; base-uri 'none'; form-action 'none'; object-src 'none'"
            "; require-trusted-types-for 'script'; trusted-types kinmoor 'allow-duplicates'")

def finish(src_html, out_path):
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    tmp = '_source/build-tmp-' + out_path.replace('/', '-') + '.full.html'
    open(tmp, 'w', encoding='utf-8').write(src_html)
    subprocess.run(['node', MIN, tmp, out_path], check=True)
    html = open(out_path, encoding='utf-8').read()
    html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="' + csp_for(html) + '">', 1)
    open(out_path, 'w', encoding='utf-8').write(html)
    os.remove(tmp)

# ---------- text ----------
SKIP = re.compile(r'(<script\b[\s\S]*?</script>|<style\b[\s\S]*?</style>|<svg\b[\s\S]*?</svg>|<title>[\s\S]*?</title>|<!--[\s\S]*?-->)')
LETTER = re.compile(r'[^\W\d_]')

def runs(frag):
    """The text a reader meets: runs between tags, and the attributes assistive technology reads."""
    out = []
    for i, part in enumerate(SKIP.split(frag)):
        if i % 2: continue
        out += [m.strip() for m in re.findall(r'>([^<]+)<', part) if LETTER.search(m)]
        out += [m[1] for m in re.findall(r'\b(aria-label|title|placeholder|alt)="([^"]*)"', part) if LETTER.search(m[1])]
    return out

def translate(frag, l, missing, extra_keep=()):
    if l == 'en': return frag
    table = D[l]['text']; keep = set(EN['keep']) | set(D[l].get('keep', [])) | set(extra_keep)
    def tr(t):
        s = t.strip()
        if not LETTER.search(s): return t
        if s in table: return t.replace(s, table[s], 1)
        if s not in keep: missing.add(s)
        return t
    out = []
    for i, part in enumerate(SKIP.split(frag)):
        if i % 2: out.append(part); continue
        part = re.sub(r'>([^<]+)<', lambda m: '>' + tr(m.group(1)) + '<', part)
        part = re.sub(r'\b(aria-label|title|placeholder|alt)="([^"]*)"', lambda m: m.group(1) + '="' + tr(m.group(2)) + '"', part)
        out.append(part)
    return ''.join(out)

STRINGS = {}
def t_table(l):
    t = dict(EN['t']); t.update(D[l].get('t', {}))
    missing = [k for k in EN['t'] if l != 'en' and k not in D[l].get('t', {})]
    if missing: sys.exit(f'{l}: script phrases missing: {missing}')
    # the suggestion note, in each public language other than this page's
    t['sug'] = {o: {'note': D[o]['ui']['note'], 'go': D[o]['ui']['go'], 'close': D[o]['ui']['close'], 'href': home(o)} for o in PUBLIC if o != l}
    STRINGS[l] = [v for k, v in t.items() if isinstance(v, str)] + [x for g in t['sug'].values() for x in (g['note'], g['go'])]
    return json.dumps(t, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')

# ---------- fonts ----------
def font_manifest():
    try: return json.load(open('fonts/manifest.json', encoding='utf-8'))
    except FileNotFoundError: return {}
MANIFEST = font_manifest()
def _source_hash():
    h = hashlib.sha256()
    for f in sorted(['_source/page.html', '_source/privacy.html'] + [f'_source/i18n/{l}.json' for l in LANGS]): h.update(open(f, 'rb').read())
    return h.hexdigest()[:16]
if MANIFEST and MANIFEST.get('_source') != _source_hash() and not os.environ.get('FONTS_PENDING'):
    print('warning: the text has changed since the fonts were cut. Build with PUBLIC=en,es,fr,de,ja, run tools/fonts.py, then build again.')

def tag(path):
    return hashlib.sha256(open(path.lstrip('/'), 'rb').read()).hexdigest()[:8]

def fonts_for(l):
    """(preload links, @font-face rules, extra CSS) for a language. English keeps its original files and tags."""
    m = MANIFEST.get(l)
    if not m:
        if l != 'en' and not os.environ.get('FONTS_PENDING'): sys.exit(f'{l}: no fonts yet. Build with FONTS_PENDING=1, run tools/fonts.py, then build again.')
        return None
    pre, faces = [], []
    for f in m['files']:
        url = '/' + f['file'] + '?v=' + (f.get('v') or tag(f['file']))
        if f.get('preload'): pre.append(f'<link rel="preload" href="{url}" as="font" type="font/woff2" crossorigin>')
        rng = (';unicode-range:' + f['range']) if f.get('range') else ''
        extra = (';font-stretch:' + f['stretch']) if f.get('stretch') else ''
        faces.append('@font-face{font-family:"%s";src:url("%s") format("woff2");font-weight:%s%s;font-display:swap%s}' % (f['family'], url, f['weight'], extra, rng))
    return '\n'.join(pre), '\n'.join(faces), m.get('css', '')

FONT_FACES_EN = re.compile(r'(@font-face\{font-family:"(?:Archivo|Kinmoor Text|IBM Plex Mono)";src:url\("/fonts/[^}]*\}\n)+')
PRELOADS_EN = re.compile(r'(<link rel="preload" href="/fonts/[^>]*>\n)+')

# ---------- language switcher ----------
def switcher(l):
    shown = [o for o in LANGS if o in PUBLIC or o == l]
    if len(shown) < 2: return ''
    items = ''.join(f'<li><a href="{home(o)}" hreflang="{o}" lang="{o}"' + (' aria-current="true"' if o == l else '') + f'>{D[o]["name"]}</a></li>' for o in shown)
    # The visible code starts the spoken name ("ES, Idioma: Español"), so speech control can use what it sees (WCAG 2.5.3).
    return (f'<details class="lang"><summary title="{D[l]["ui"]["language"]}">{l.upper()}<span class="vh">, {D[l]["ui"]["language"]}: {D[l]["name"]}</span>'
            f'</summary><ul>{items}</ul></details>')

def alternates(path_for):
    if len(PUBLIC) < 2: return ''
    links = [f'<link rel="alternate" hreflang="{o}" href="{SITE}{path_for(o)}">' for o in PUBLIC]
    links.append(f'<link rel="alternate" hreflang="x-default" href="{SITE}{path_for("en")}">')
    return '\n'.join(links)

def robots(l):
    return '' if l in PUBLIC else '<meta name="robots" content="noindex">'

HEAD_COMMON = '''<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#ECEEE8" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#111310" media="(prefers-color-scheme: dark)">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">'''

def hand(l, body):
    """Swap the hand-drawn words (traced by tools/hand.py) into the hint and the bin's note."""
    if l == 'en': return body
    hd = json.load(open('_source/i18n/hand.json', encoding='utf-8'))[l]
    body, n1 = re.subn(r'<path class="nt" transform="[^"]*" d="[^"]*"/>', '<path class="nt" transform="%s" d="%s"/>' % (hd['click']['transform'], hd['click']['d']), body)
    body, n2 = re.subn(r'<svg class="bin-note" viewBox="[^"]*" aria-hidden="true">[\s\S]*?</svg>',
                       '<svg class="bin-note" viewBox="%s" aria-hidden="true"><path class="w1" transform="%s" d="%s"/><path class="w2" transform="%s" d="%s"/></svg>'
                       % (hd['viewBox'], hd['w1']['transform'], hd['w1']['d'], hd['w2']['transform'], hd['w2']['d']), body)
    if n1 != 1 or n2 != 1: sys.exit(f'{l}: hand-drawn words not found in page.html')
    return body

# ---------- home pages ----------
frag = open('_source/page.html', encoding='utf-8').read()
cut = frag.index('</style>') + len('</style>')
head_src = frag[:cut].replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
head_src = re.sub(r'<link rel="icon" href="data:[^"]*">\n', '', head_src)
body_src = frag[cut:]
needed = {}
problems = []

for l in LANGS:
    M = D[l]['meta']; missing = set()
    body = body_src
    if l != 'en':
        body, n = re.subn(r'(<h1[^>]*>)[\s\S]*?(</h1>)', lambda m: m.group(1) + D[l]['h1'] + m.group(2), body, count=1)
        if n != 1: sys.exit('h1 not found')
        body = body.replace('href="/privacy"', f'href="{privacy(l)}"')
    body = hand(l, body)
    body = translate(body, l, missing, extra_keep=runs('>' + D[l].get('h1', '') + '<'))
    body = body.replace('<!--LANG-->', switcher(l))
    body = body.replace('I18N_T', t_table(l))
    head = head_src.replace('<title>Kinmoor Studios</title>', f'<title>{M["title"]}</title>')
    head = head.replace('"urls":["/privacy"]', f'"urls":["{privacy(l)}"]')
    fs = fonts_for(l)
    if fs:
        head, a = PRELOADS_EN.subn(fs[0] + '\n', head, count=1)
        head, b = FONT_FACES_EN.subn(fs[1] + '\n' + (fs[2] + '\n' if fs[2] else ''), head, count=1)
        if a != 1 or b != 1: sys.exit('font links not found in page.html')
    org = {"@context": "https://schema.org", "@type": "Organization", "name": "Kinmoor Studios", "legalName": "Kinmoor Studios, LLC",
           "url": SITE + '/', "logo": SITE + "/icon-512.png", "email": "hello@kinmoorstudios.com", "description": M['description']}
    locales = ''.join(f'\n<meta property="og:locale:alternate" content="{D[o]["og_locale"]}">' for o in PUBLIC if o != l) if l in PUBLIC else ''
    doc = f'''<!DOCTYPE html>
<html lang="{l}">
<head>
{HEAD_COMMON}
<meta name="description" content="{M['description']}">
{robots(l)}
<meta property="og:site_name" content="Kinmoor Studios">
<meta property="og:title" content="Kinmoor Studios">
<meta property="og:description" content="{M['og_description']}">
<meta property="og:url" content="{SITE}{home(l)}">
<meta property="og:type" content="website">
<meta property="og:locale" content="{D[l]['og_locale']}">{locales}
<meta property="og:image" content="{SITE}/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{M['og_image_alt']}">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{SITE}{home(l)}">
{alternates(home) if l in PUBLIC else ''}
<script type="application/ld+json">{json.dumps(org, ensure_ascii=False, separators=(',', ':'))}</script>
{head}
</head>
<body>{body}
</body>
</html>
'''
    doc = re.sub(r'\n{2,}', '\n', doc)
    if missing: problems.append(f'{l}: {len(missing)} untranslated: ' + ' | '.join(sorted(missing)))
    needed[l] = {'home': 'index.html' if l == 'en' else f'{l}/index.html'}
    finish(doc, needed[l]['home'])

# ---------- privacy pages and 404 share one small template ----------
SMALL_CSS = open('_source/small.css', encoding='utf-8').read()
PRIVACY_EN = open('_source/privacy.html', encoding='utf-8').read()

def small_page(l, path, title, desc, body, canonical, alt_html, extra_head='', prefetch='/'):
    fs = fonts_for(l)
    css = SMALL_CSS
    if fs: css = FONT_FACES_EN.sub(fs[1] + '\n' + (fs[2] + '\n' if fs[2] else ''), css, count=1)
    page = f'''<!DOCTYPE html>
<html lang="{l}">
<head>
{HEAD_COMMON}
<title>{title}</title>
<meta name="description" content="{desc}">
{robots(l) if path != '404.html' else ''}
{f'<link rel="canonical" href="{SITE}{canonical}">' if canonical else ''}
{alt_html}
<style>{css}</style>
<script>try{{var t=localStorage.getItem('kinmoor-theme');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}}catch(e){{}}</script>
{extra_head}<script type="speculationrules">{{"prefetch":[{{"source":"list","urls":["{prefetch}"],"eagerness":"moderate"}}]}}</script>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
'''
    finish(re.sub(r'\n{2,}', '\n', page), path)

for l in LANGS:
    M = D[l]['meta']; missing = set()
    body = translate(PRIVACY_EN.replace('href="/"', f'href="{home(l)}"'), l, missing)
    if missing: problems.append(f'{l} privacy: {len(missing)} untranslated: ' + ' | '.join(sorted(missing)))
    path = 'privacy.html' if l == 'en' else f'{l}/privacy.html'
    small_page(l, path, M['privacy_title'], M['privacy_description'], body, privacy(l), alternates(privacy) if l in PUBLIC else '', prefetch=home(l))

# 404: GitHub Pages serves one 404.html for every missing address, so the page picks its language from the address (/es/...).
nf = {o: {'eyebrow': D[o]['notfound']['eyebrow'], 'h1': D[o]['notfound']['h1'], 'p': D[o]['notfound']['p'], 'home': D[o]['notfound']['home'],
          'href': home(o), 'title': D[o]['meta']['notfound_title']} for o in PUBLIC if o != 'en'}
nf_script = ('<script>(function(){var d=%s,l=location.pathname.split("/")[1],t=d[l];if(!t)return;var r=document.documentElement;r.lang=l;document.title=t.title;'
             'var q=function(s){return document.querySelector(s)};q(".eyebrow").textContent=t.eyebrow;q("h1").textContent=t.h1;q("main p:not(.eyebrow)").textContent=t.p;'
             'var a=q(".home");a.textContent=t.home;a.href=t.href})()</script>\n') % json.dumps(nf, ensure_ascii=False, separators=(',', ':')) if nf else ''
NF = EN['notfound']
small_page('en', '404.html', EN['meta']['notfound_title'], 'This page does not exist.',
           f'''<p class="eyebrow">{NF['eyebrow']}</p>\n<h1>{NF['h1']}</h1>\n<p>{NF['p']}</p>\n<a class="home" href="/">{NF['home']}</a>''' + ('\n' + nf_script if nf_script else ''),
           None, '')

# ---------- sitemap ----------
today = os.environ.get('LASTMOD') or subprocess.run(['date', '+%Y-%m-%d'], capture_output=True, text=True).stdout.strip()
urls = []
for path_for in (home, privacy):
    for l in PUBLIC:
        alts = ''.join(f'<xhtml:link rel="alternate" hreflang="{o}" href="{SITE}{path_for(o)}"/>' for o in PUBLIC) if len(PUBLIC) > 1 else ''
        if alts: alts += f'<xhtml:link rel="alternate" hreflang="x-default" href="{SITE}{path_for("en")}"/>'
        urls.append(f'<url><loc>{SITE}{path_for(l)}</loc><lastmod>{today}</lastmod>{alts}</url>')
open('sitemap.xml', 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + '\n'.join(urls) + '\n</urlset>\n')

json.dump(STRINGS, open('_source/build-strings.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
if problems:
    print('\n'.join(problems)); sys.exit(1)
print('built:', ', '.join(LANGS), '| public:', ', '.join(PUBLIC))
