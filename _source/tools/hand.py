# Traces the hand-drawn words for each language into SVG paths (_source/i18n/hand.json), so no handwriting font is ever downloaded.
# Latin scripts use Caveat SemiBold; Japanese uses Klee One SemiBold (both SIL OFL 1.1).
# Usage: python3 _source/tools/hand.py CAVEAT_600.woff2 KLEEONE_600.ttf
# Each word is placed where the English one sits: the "Click me" hint keeps its centre over the arrow and its baseline,
# growing at most 20% wider; the bin's words end at the same point beside the bin and share the height of "Tasty!".
import json, sys
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

class RelPen(BasePen):
    """Compact SVG path: whole-number, relative coordinates."""
    def __init__(s, gs):
        super().__init__(gs); s.out = []; s.cx = s.cy = s.sx = s.sy = 0
    def r(s, p): return int(round(p[0])), int(round(p[1]))
    def j(s, vals):
        o = ''
        for v in vals:
            t = '%d' % v; o += t if (o == '' or t.startswith('-')) else ' ' + t
        return o
    def _moveTo(s, p):
        x, y = s.r(p); s.out.append('m' + s.j([x - s.cx, y - s.cy])); s.cx, s.cy = x, y; s.sx, s.sy = x, y
    def _lineTo(s, p):
        x, y = s.r(p); dx, dy = x - s.cx, y - s.cy
        if dx or dy: s.out.append('l' + s.j([dx, dy]))
        s.cx, s.cy = x, y
    def _qCurveToOne(s, p1, p2):
        a = s.r(p1); b = s.r(p2); s.out.append('q' + s.j([a[0] - s.cx, a[1] - s.cy, b[0] - s.cx, b[1] - s.cy])); s.cx, s.cy = b
    def _curveToOne(s, p1, p2, p3):
        a = s.r(p1); b = s.r(p2); c = s.r(p3)
        s.out.append('c' + s.j([a[0] - s.cx, a[1] - s.cy, b[0] - s.cx, b[1] - s.cy, c[0] - s.cx, c[1] - s.cy])); s.cx, s.cy = c
    def _closePath(s):
        s.out.append('z'); s.cx, s.cy = s.sx, s.sy

def trace(font_path, text, size=56):
    f = TTFont(font_path); gs = f.getGlyphSet(); cmap = f.getBestCmap(); upm = f['head'].unitsPerEm; hmtx = f['hmtx']
    sc = size / upm; asc = f['hhea'].ascent; pen = RelPen(gs); bp = BoundsPen(gs); x = 0
    for ch in text.replace('\xa0', ' '):
        g = cmap[ord(ch)]; m = (sc, 0, 0, -sc, x, asc * sc)
        gs[g].draw(TransformPen(pen, m)); gs[g].draw(TransformPen(bp, m)); x += hmtx[g][0] * sc
    d = ''.join(pen.out); d = 'M' + d[1:]
    return d, bp.bounds  # (xmin, ymin, xmax, ymax), y down

def r2(v): return ('%.2f' % v).rstrip('0').rstrip('.')

if __name__ == '__main__':
    caveat, klee = sys.argv[1], sys.argv[2]
    D = {l: json.load(open(f'_source/i18n/{l}.json', encoding='utf-8')) for l in ('en', 'es', 'fr', 'de', 'ja')}
    _, ec = trace(caveat, D['en']['hand']['click'])      # English hint: transform="translate(0 2) rotate(-4) scale(.42)"
    _, et = trace(caveat, D['en']['hand']['w2'])         # "Tasty!": ends at x=130 in a 132-wide note
    ecx = .42 * (ec[0] + ec[2]) / 2; ebottom = .42 * ec[3] + 2; ew = ec[2] - ec[0]
    tcy = (et[1] + et[3]) / 2; th = et[3] - et[1]
    out = {}
    for l in ('es', 'fr', 'de', 'ja'):
        font = klee if l == 'ja' else caveat; h = D[l]['hand']; o = {'viewBox': '0 0 132 71'}
        d, b = trace(font, h['click'])
        s = .42 * min(1, ew * 1.2 / (b[2] - b[0]))
        if l == 'ja': s = min(s, .42 * th / (b[3] - b[1]) * 1.05)
        tx = ecx - s * (b[0] + b[2]) / 2; ty = ebottom - s * b[3]
        o['click'] = {'d': d, 'transform': f'translate({r2(tx)} {r2(ty)}) rotate(-4) scale({r2(s)})'}
        for k in ('w1', 'w2'):
            d, b = trace(font, h[k])
            # Kana and kanji fill their whole em, so they are set smaller, and no wider than about 1.4 times "Tasty!".
            s = 1 if l != 'ja' else min(th / (b[3] - b[1]) * .85, 170 / (b[2] - b[0]))
            tx = 130 - s * b[2]; ty = tcy - s * (b[1] + b[3]) / 2
            o[k] = {'d': d, 'transform': f'translate({r2(tx)} {r2(ty)})' + (f' scale({r2(s)})' if s != 1 else '')}
        out[l] = o
    json.dump(out, open('_source/i18n/hand.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('traced:', ', '.join(f"{l}: {D[l]['hand']['click']} / {D[l]['hand']['w1']} / {D[l]['hand']['w2']}" for l in out))
