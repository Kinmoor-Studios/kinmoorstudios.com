# Font subsets for every language, cut to the characters each font actually draws on each page.
# Usage, from the repository root, after a build:
#   python3 _source/tools/fonts.py LATIN_SRC JP_SRC
#     LATIN_SRC: a node_modules folder with @fontsource-variable/archivo, @fontsource-variable/source-serif-4, @fontsource/ibm-plex-mono
#     JP_SRC:    a node_modules folder with @expo-google-fonts/noto-sans-jp, noto-serif-jp, ibm-plex-sans-jp
# then build again so the pages link the new files.
#
# How: each built page is opened in a browser; every text node is attributed to the first family in its computed font stack
# (and its weight), the script's own phrases are added to the label font, and each font is subset to exactly that.
# English keeps its original four files (the CDN's font hints name them); characters they lack, such as the switcher's
# "Español" or "日本語", come from small extra files that unicode-range keeps from downloading until those characters show.
# Japanese pairs the Latin fonts with Noto Sans JP (headings), Noto Serif JP (text), and IBM Plex Sans JP (labels).
import json, os, sys, threading, http.server, functools, io, hashlib
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from playwright.sync_api import sync_playwright

LATIN, JP = sys.argv[1], sys.argv[2]
SRC = {
    'archivo': f'{LATIN}/@fontsource-variable/archivo/files/archivo-latin-wdth-normal.woff2',
    'serif': f'{LATIN}/@fontsource-variable/source-serif-4/files/source-serif-4-latin-opsz-normal.woff2',
    'mono400': f'{LATIN}/@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-400-normal.woff2',
    'mono500': f'{LATIN}/@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-500-normal.woff2',
    'jpdisplay': f'{JP}/@expo-google-fonts/noto-sans-jp/800ExtraBold/NotoSansJP_800ExtraBold.ttf',
    'jptext': f'{JP}/@expo-google-fonts/noto-serif-jp/400Regular/NotoSerifJP_400Regular.ttf',
    'jpsans': f'{JP}/@expo-google-fonts/ibm-plex-sans-jp/500Medium/IBMPlexSansJP_500Medium.ttf',
}
LANGS = ['en', 'es', 'fr', 'de', 'ja']
D = {l: json.load(open(f'_source/i18n/{l}.json', encoding='utf-8')) for l in LANGS}
STRINGS = json.load(open('_source/build-strings.json', encoding='utf-8'))   # the script's phrases per page, written by the build
BASE = set(chr(c) for c in range(0x20, 0x7f)) | set('©°·×–—‘’“”…\xa0')
EN_FILES = [  # the originals, unchanged
    {'file': 'fonts/archivo-display.woff2', 'v': '2607a15a', 'family': 'Archivo', 'weight': '700 800', 'stretch': '112% 125%', 'preload': True, 'role': 'display'},
    {'file': 'fonts/kinmoor-text.woff2', 'v': '77a883ec', 'family': 'Kinmoor Text', 'weight': '400', 'preload': True, 'role': 'text'},
    {'file': 'fonts/ibm-plex-mono-500.woff2', 'v': '723c5326', 'family': 'IBM Plex Mono', 'weight': '500', 'preload': True, 'role': 'mono500'},
    {'file': 'fonts/ibm-plex-mono-400.woff2', 'v': '6b380ffd', 'family': 'IBM Plex Mono', 'weight': '400', 'preload': True, 'role': 'mono400'},
]
FEATURES = ['ccmp', 'liga', 'locl', 'kern', 'mark', 'mkmk', 'pnum', 'tnum', 'palt']
JP_CSS = '''html:lang(ja){--display:"Archivo","Kinmoor JP Display","Archivo Fallback","Hiragino Sans","Yu Gothic",sans-serif;--serif:"Kinmoor Text","Kinmoor JP Text","Kinmoor Text Fallback","Hiragino Mincho ProN","Yu Mincho",serif;--mono:"IBM Plex Mono","Kinmoor JP Sans","Plex Mono Fallback","Hiragino Sans","Yu Gothic",monospace}
/* Japanese: no letter-spacing or capitals, proportional kana in headings, line breaks between phrases (Chrome 119+), and no breaks before small kana or closing punctuation. */
:lang(ja) body{line-break:strict;word-break:normal;overflow-wrap:anywhere}
:lang(ja) h1,:lang(ja) h2,:lang(ja) h3{font-feature-settings:"palt";letter-spacing:0;word-break:auto-phrase}
:lang(ja) .eyebrow,:lang(ja) .tag,:lang(ja) .btn,:lang(ja) th,:lang(ja) .lang-note p{word-break:auto-phrase}
:lang(ja) h1{line-height:1.1}
:lang(ja) p,:lang(ja) li,:lang(ja) dd,:lang(ja) td{line-height:1.85;letter-spacing:.02em}
:lang(ja) .eyebrow,:lang(ja) .tag,:lang(ja) .nav,:lang(ja) .btn,:lang(ja) th,:lang(ja) .step h3{letter-spacing:.04em}'''

def cmap(path):
    return set(chr(c) for c in TTFont(path).getBestCmap())

def make(src, chars, out, axes=None, family=None):
    f = TTFont(src)
    if axes: f = instancer.instantiateVariableFont(f, axes)
    o = subset.Options(); o.flavor = 'woff2'; o.layout_features = FEATURES; o.hinting = False; o.name_IDs = [0, 1, 2, 3, 4, 5, 6]
    o.notdef_outline = True; o.drop_tables += ['DSIG']
    s = subset.Subsetter(o); s.populate(unicodes=[ord(c) for c in chars]); s.subset(f)
    if family:
        for rec in f['name'].names:
            if rec.nameID in (1, 16): rec.string = family
            elif rec.nameID == 4: rec.string = family + ' Regular'
            elif rec.nameID == 6: rec.string = family.replace(' ', '') + '-Regular'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    f.save(out)
    return os.path.getsize(out)

def urange(chars):
    cps = sorted(ord(c) for c in chars); parts = []; i = 0
    while i < len(cps):
        j = i
        while j + 1 < len(cps) and cps[j + 1] == cps[j] + 1: j += 1
        parts.append('U+%X' % cps[i] if i == j else 'U+%X-%X' % (cps[i], cps[j])); i = j + 1
    return ','.join(parts)

COLLECT = r'''() => {
  const out = {}, first = {};
  const add = (el, text) => {
    if (!el || !text) return;
    const cs = getComputedStyle(el); const fam = cs.fontFamily.split(',')[0].trim().replace(/^["']|["']$/g, '');
    const key = fam + '|' + (parseInt(cs.fontWeight) >= 500 ? (fam === 'IBM Plex Mono' ? 500 : 700) : 400);
    out[key] = (out[key] || '') + text;
    const r = el.getBoundingClientRect();
    if (r.bottom > 0 && r.top < innerHeight && r.width > 1 && cs.visibility !== 'hidden') first[key] = (first[key] || '') + text;
  };
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n; while ((n = w.nextNode())) { if (n.parentElement && !n.parentElement.closest('script,style,svg')) add(n.parentElement, n.nodeValue) }
  document.querySelectorAll('input[placeholder]').forEach(i => add(i, i.placeholder));
  document.querySelectorAll('*').forEach(el => { for (const p of ['::before', '::after']) { const c = getComputedStyle(el, p).content; if (c && c !== 'none' && c.startsWith('"')) add(el, c.slice(1, -1)) } });
  return {out, first};
}'''

def serve():
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Q, directory='.'))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]

def page_path(l, kind):
    if kind == 'home': return '/' if l == 'en' else f'/{l}/'
    return '/privacy.html' if l == 'en' else f'/{l}/privacy.html'

port = serve()
need = {}; first = {}; home_all = {}
def merge(acc, d):
    for k, v in d.items(): acc[k] = acc.get(k, '') + v
with sync_playwright() as p:
    b = p.chromium.launch()
    for l in LANGS:
        acc, fst, hm = {}, {}, {}
        for kind in ('home', 'privacy'):
            # the first screen at phone and laptop sizes
            for vw, vh in ((390, 844), (1366, 900)):
                pg = b.new_page(viewport={'width': vw, 'height': vh}); pg.goto(f'http://127.0.0.1:{port}{page_path(l, kind)}'); pg.wait_for_timeout(400)
                r = pg.evaluate(COLLECT); pg.close()
                merge(acc, r['out'])
                if kind == 'home': merge(fst, r['first']); merge(hm, r['out'])
        # the script's phrases appear in the label font, at both weights: status words on the first screen, the decode's scramble later
        t = STRINGS.get(l, []); scr = D[l]['t'].get('scr', D['en']['t']['scr'])
        for k in ('IBM Plex Mono|400', 'IBM Plex Mono|500'):
            merge(acc, {k: ''.join(t)}); merge(fst, {k: ''.join(x for x in t if x != scr)}); merge(hm, {k: ''.join(t)})
        clean = lambda d: {k: set(v) - set('\n\t\r') for k, v in d.items()}
        need[l], first[l], home_all[l] = clean(acc), clean(fst), clean(hm)
    b.close()

ROLE = {'Archivo|700': 'display', 'Archivo|400': 'display', 'Kinmoor Text|400': 'text', 'Kinmoor Text|700': 'text', 'IBM Plex Mono|400': 'mono400', 'IBM Plex Mono|500': 'mono500'}
manifest = {}; report = []
def is_cjk(c): return ord(c) >= 0x2E80
for l in LANGS:
    roles = {'display': set(), 'text': set(), 'mono400': set(), 'mono500': set()}
    for k, chars in need[l].items():
        if k in ROLE: roles[ROLE[k]] |= chars
        else: print(f'  {l}: ignoring text in "{k}"')
    files = []
    if l == 'ja':
        files = [dict(f) for f in EN_FILES]
        for f in files: f['preload'] = f['role'] == 'display'
        jp = {'display': ('jpdisplay', 'Kinmoor JP Display', '700 800', True), 'text': ('jptext', 'Kinmoor JP Text', '400', True), 'mono': ('jpsans', 'Kinmoor JP Sans', '400 500', False)}
        groups = {'display': roles['display'], 'text': roles['text'], 'mono': roles['mono400'] | roles['mono500']}
        def by_group(d, g):
            keys = {'display': ('Archivo|700', 'Archivo|400'), 'text': ('Kinmoor Text|400', 'Kinmoor Text|700'), 'mono': ('IBM Plex Mono|400', 'IBM Plex Mono|500')}[g]
            return set().union(*[d.get(k, set()) for k in keys])
        for g, chars in groups.items():
            have = cmap(next(f['file'] for f in EN_FILES if f['role'] == ('mono500' if g == 'mono' else g)))
            missing = {c for c in chars if c not in have and not c.isspace()}
            a = missing & by_group(first[l], g); bb = (missing & by_group(home_all[l], g)) - a; c = missing - a - bb
            src, fam, wt, pre = jp[g]; base = fam.lower().replace(' ', '-')
            for part, cs, pl in (('first', a, pre), ('page', bb, False), ('privacy', c, False)):
                if not cs: continue
                out = f'fonts/ja/{base}-{part}.woff2'; size = make(SRC[src], cs, out)
                files.append({'file': out, 'family': fam, 'weight': wt, 'preload': pl, 'range': urange(cs), 'role': g})
                report.append(f'{l} {fam} ({part}): {len(cs)} characters, {size/1024:.1f} KB' + (', preloaded' if pl else ', loads when shown'))
        manifest[l] = {'files': files, 'css': JP_CSS}
    else:
        if l == 'en':
            files = [dict(f) for f in EN_FILES]
            have = {f['role']: cmap(f['file']) for f in EN_FILES}
            latin_extra = set(); cjk_extra = set()
            for r, chars in roles.items():
                for c in {x for x in chars - have[r] if not x.isspace()}:
                    (cjk_extra if is_cjk(c) else latin_extra).add(c)
                    if not is_cjk(c) and not r.startswith('mono'): print(f'  en: {r} lacks {c!r}, served by the label font extra')
        else:
            spec = {'display': ('archivo', 'archivo-display', 'Archivo', '700 800', '112% 125%', {'wght': (700, 800), 'wdth': (112, 125)}, None),
                    'text': ('serif', 'kinmoor-text', 'Kinmoor Text', '400', None, {'wght': 400, 'opsz': (16, 24)}, 'Kinmoor Text'),
                    'mono500': ('mono500', 'ibm-plex-mono-500', 'IBM Plex Mono', '500', None, None, None),
                    'mono400': ('mono400', 'ibm-plex-mono-400', 'IBM Plex Mono', '400', None, None, None)}
            cjk_extra = set(); latin_extra = set()
            for r, (src, name, fam, wt, st, axes, rename) in spec.items():
                chars = {c for c in roles[r] if not is_cjk(c)} | BASE
                cjk_extra |= {c for c in roles[r] if is_cjk(c)}
                out = f'fonts/{l}/{name}.woff2'; size = make(SRC[src], chars, out, axes, rename)
                e = {'file': out, 'family': fam, 'weight': wt, 'preload': True, 'role': r}
                if st: e['stretch'] = st
                files.append(e); report.append(f'{l} {name}: {len(chars)} characters, {size/1024:.1f} KB')
        if latin_extra:
            for wt in ('400', '500'):
                out = f'fonts/extra/ibm-plex-mono-{wt}-' + hashlib.sha256(''.join(sorted(latin_extra)).encode()).hexdigest()[:8] + '.woff2'; size = make(SRC['mono' + wt], latin_extra, out)
                files.append({'file': out, 'family': 'IBM Plex Mono', 'weight': wt, 'preload': False, 'range': urange(latin_extra), 'role': 'extra'})
                report.append(f'{l} label extra {wt}: {"".join(sorted(latin_extra))} ({size/1024:.1f} KB, loads only when shown)')
        if cjk_extra:
            # the same characters on every page share one file, cached once
            out = 'fonts/extra/japanese-labels-' + hashlib.sha256(''.join(sorted(cjk_extra)).encode()).hexdigest()[:8] + '.woff2'; size = make(SRC['jpsans'], cjk_extra, out)
            files.append({'file': out, 'family': 'IBM Plex Mono', 'weight': '400 500', 'preload': False, 'range': urange(cjk_extra), 'role': 'extra'})
            report.append(f'{l} Japanese label extra: {len(cjk_extra)} characters ({size/1024:.1f} KB, loads only when shown)')
        manifest[l] = {'files': files}
def source_hash():
    h = hashlib.sha256()
    for f in sorted(['_source/page.html', '_source/privacy.html'] + [f'_source/i18n/{l}.json' for l in LANGS]): h.update(open(f, 'rb').read())
    return h.hexdigest()[:16]
manifest['_source'] = source_hash()   # the build warns when the text has changed since these fonts were cut
json.dump(manifest, open('fonts/manifest.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n'.join(report))
