# kinmoorstudios.com source

The published files at the repository root are built from this folder: the home and privacy pages in every language (English at `/`, the others at `/es/`, `/fr/`, `/de/`, `/ja/`), `404.html`, `sitemap.xml`, and the per-language fonts in `/fonts`.
GitHub Pages skips folders whose names start with an underscore, so nothing here is published.

## Build

From the repository root, with Python 3 and Node.js installed:

```
npm install --prefix _source/tools terser@5.36.0 csso@5.0.5
NODE_PATH=_source/tools/node_modules python3 _source/build.py
```

The build:
- minifies the inline CSS and JavaScript (`tools/min.js`);
- adds a Content-Security-Policy whose script and style hashes match the minified code. Edit `page.html`, never the built `index.html`, or the hashes won't match and the browser will block the page's own code;
- stops if any text in any language is missing a translation.

## Languages

Each language is one file in `i18n/`: `en.json` holds the English reference (the script's phrases, the switcher and suggestion wording, and text that stays the same everywhere); the others hold the translations.

- **`text`**: every run of text between tags in `page.html` and `privacy.html`, plus every `aria-label`, `title`, `placeholder` and `alt`, keyed by its exact English. A missing key stops the build and lists what's missing.
- **`t`**: the phrases the page's script shows (the live readout, copy, theme and motion buttons). They replace `I18N_T` in `page.html`. Numbers are formatted for the page's language by the browser (`1.8 s`, `1,8 s`).
- **`h1`**: the hero headline, written per language as three lines.
- **`hand`**: the hand-drawn words. `tools/hand.py` traces them into SVG shapes (`i18n/hand.json`): Caveat for Latin scripts, Klee One for Japanese.
- **`reviewed`**: a language goes public when this is `true`. Until then its pages exist for reviewers but carry `noindex` and are left out of the switcher, the suggestion note, `hreflang` and the sitemap. `PUBLIC=en,es,fr,de,ja` previews everything as public (for testing only).

The note that offers another language appears once, a moment after load, when the first of the browser's preferred languages that the site has isn't the page's own. It never redirects, and closing it is remembered.

## Fonts

English keeps its original four files in `/fonts` (Cloudflare's "Font hints" rule names their `?v=` tags; if one changes, update the tag there too).
Every other language gets subsets cut to the characters each font actually draws on its pages:

```
PUBLIC=en,es,fr,de,ja FONTS_PENDING=1 NODE_PATH=_source/tools/node_modules python3 _source/build.py
python3 _source/tools/fonts.py LATIN_SRC JP_SRC
NODE_PATH=_source/tools/node_modules python3 _source/build.py
```

`LATIN_SRC` and `JP_SRC` are `node_modules` folders with the source fonts (`npm install @fontsource-variable/archivo @fontsource-variable/source-serif-4 @fontsource/ibm-plex-mono` and `npm install @expo-google-fonts/noto-sans-jp @expo-google-fonts/noto-serif-jp @expo-google-fonts/ibm-plex-sans-jp @expo-google-fonts/klee-one`).
`fonts.py` opens each built page in a browser, attributes every piece of text to the font that draws it, and writes the subsets and `fonts/manifest.json`. Japanese fonts are split three ways with `unicode-range`: the first screen (preloaded), the rest of the page (downloaded when those sections draw), and the privacy page. Characters a page shows only on demand, such as the switcher's "日本語" on a Latin page, come from small extra files in `fonts/extra/` that download only when shown. The build warns when text has changed since the fonts were cut.

## Files

- `page.html`: the home page source (styles, markup and script in one file).
- `privacy.html`, `small.css`: the privacy page's English text and the small pages' styles.
- `build.py`: builds everything above.
- `i18n/`: the languages; `hand.json` is generated.
- `tools/fonts.py`, `tools/hand.py`: font subsets and hand-drawn words, as above.
- `tools/local-server.py`: serves the site locally the way GitHub Pages does (gzip, 10-minute cache): `python3 _source/tools/local-server.py . 8766`.
- `tools/scroll-benchmark.py`: the scrolling smoothness test used to compare versions (needs Playwright).
- `tools/og-image.py`: recaptures the social preview image (`og.jpg`, 1200 × 630) from a local copy of the site: `python3 _source/tools/og-image.py http://127.0.0.1:8766/ og.jpg` (needs Playwright and Pillow).

Fonts: Archivo, IBM Plex Mono, IBM Plex Sans JP, Noto Sans JP and Noto Serif JP, and Source Serif 4 (renamed Kinmoor Text) are under the SIL Open Font License 1.1; their licences are in `/fonts`. The hand-drawn words are traced from Caveat (copyright 2014 The Caveat Project Authors) and Klee One (copyright 2020 The Klee Project Authors), both SIL Open Font License 1.1, into SVG shapes; no handwriting font is loaded.
