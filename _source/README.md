# kinmoorstudios.com source

The published files at the repository root (`index.html`, `404.html`, `privacy.html`) are built from this folder.
GitHub Pages skips folders whose names start with an underscore, so nothing here is published.

## Build

From the repository root, with Python 3 and Node.js installed:

```
npm install --prefix _source/tools terser@5.36.0 csso@5.0.5
NODE_PATH=_source/tools/node_modules python3 _source/build.py
```

The build:
- minifies the inline CSS and JavaScript (`tools/min.js`);
- adds a Content-Security-Policy whose script and style hashes match the minified code. Edit `page.html`, never the built `index.html`, or the hashes won't match and the browser will block the page's own code.

## Files

- `page.html`: the home page source (styles, markup and script in one file).
- `build.py`: builds `index.html`, `404.html` and `privacy.html`.
- `parts/`: earlier working copies of the hero and test-section scripts, kept for reference. `page.html` is the source of truth.
- `tools/local-server.py`: serves the site locally the way GitHub Pages does (gzip, 10-minute cache): `python3 _source/tools/local-server.py . 8766`.
- `tools/scroll-benchmark.py`: the scrolling smoothness test used to compare versions (needs Playwright).

Fonts in `/fonts` are referenced with a `?v=` version tag. If a font file changes, update its tag in `page.html` and `build.py` so a long cache can't serve the old copy.
