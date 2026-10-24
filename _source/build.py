# Builds the deployable site: index.html (minified, with a hash-based Content-Security-Policy) plus 404.html and privacy.html.
import re, hashlib, base64, json, subprocess
MIN='_source/tools/min.js'  # run from the repository root
SITE='https://kinmoorstudios.com/'

def csp_for(html):
    """Content-Security-Policy that allows only this page's own inline code (by hash), its own fonts, and nothing else."""
    def h(text): return "'sha256-"+base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()+"'"
    scripts=[h(m) for m in re.findall(r'<script>([\s\S]*?)</script>',html)]
    styles=[h(m) for m in re.findall(r'<style>([\s\S]*?)</style>',html)]
    return ("default-src 'none'; script-src "+' '.join(scripts or ["'none'"])+"; style-src "+' '.join(styles or ["'none'"])+
            "; img-src 'self' data:; font-src 'self'; manifest-src 'self'; worker-src blob:; connect-src 'self'"
            "; base-uri 'none'; form-action 'none'; object-src 'none'"
            "; require-trusted-types-for 'script'; trusted-types kinmoor 'allow-duplicates'")

def finish(src_path, out_path):
    subprocess.run(['node',MIN,src_path,out_path],check=True)
    html=open(out_path).read()
    html=html.replace('<meta charset="utf-8">','<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="'+csp_for(html)+'">',1)
    open(out_path,'w').write(html)

HEAD_COMMON='''<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#ECEEE8" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#111310" media="(prefers-color-scheme: dark)">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">'''

ORG={"@context":"https://schema.org","@type":"Organization","name":"Kinmoor Studios","legalName":"Kinmoor Studios, LLC","url":SITE,
     "logo":SITE+"icon-512.png","email":"hello@kinmoorstudios.com","sameAs":["https://kinmoor.games"],
     "description":"Kinmoor Studios designs and builds fast, polished Shopify storefronts, apps, and back-office software for consumer brands."}

# ---------- index.html ----------
frag=open('_source/page.html').read()
i=frag.index('</style>')+len('</style>')
head=frag[:i].replace('<meta name="claude:viewport-fit-sides" content="cover">\n','')
head=re.sub(r'<link rel="icon" href="data:[^"]*">\n','',head)
doc=f'''<!DOCTYPE html>
<html lang="en">
<head>
{HEAD_COMMON}
<meta name="description" content="Kinmoor Studios designs and builds fast, polished Shopify storefronts, apps, and back-office software for consumer brands.">
<meta property="og:site_name" content="Kinmoor Studios">
<meta property="og:title" content="Kinmoor Studios">
<meta property="og:description" content="Shopify storefronts, apps, and software. Design that doesn't slow you down.">
<meta property="og:url" content="{SITE}">
<meta property="og:type" content="website">
<meta property="og:image" content="{SITE}og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Kinmoor Studios: Design that doesn't slow you down, over a contour map.">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{SITE}">
<script type="application/ld+json">{json.dumps(ORG,separators=(',',':'))}</script>
{head}
</head>
<body>{frag[i:]}
</body>
</html>
'''
open('_source/build-tmp-index.html','w').write(doc)
finish('_source/build-tmp-index.html','index.html')

# ---------- 404.html and privacy.html share one small template ----------
SMALL_CSS='''@font-face{font-family:"Archivo";src:url("/fonts/archivo-display.woff2?v=2607a15a") format("woff2");font-weight:700 800;font-stretch:112% 125%;font-display:swap}
@font-face{font-family:"Kinmoor Text";src:url("/fonts/kinmoor-text.woff2?v=77a883ec") format("woff2");font-weight:400;font-display:swap}
@font-face{font-family:"IBM Plex Mono";src:url("/fonts/ibm-plex-mono-500.woff2?v=723c5326") format("woff2");font-weight:500;font-display:swap}
:root{--ground:#ECEEE8;--ink:#1A1D17;--muted:#596155;--rule:#CBD1C4;--heather:#6B3D71}
@media (prefers-color-scheme:dark){:root{--ground:#111310;--ink:#E8EBE2;--muted:#9BA394;--rule:#2D3229;--heather:#C99FCF;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font:400 1.125rem/1.65 "Kinmoor Text",Georgia,"Times New Roman",serif}
main{max-width:44rem;margin:0 auto;padding:clamp(48px,10vw,120px) max(20px,env(safe-area-inset-right,0px)) 64px max(20px,env(safe-area-inset-left,0px))}
.eyebrow{font:500 .8125rem/1.3 "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 20px}
h1{font:800 clamp(2.4rem,7vw,4rem)/1 "Archivo","Helvetica Neue",Arial,sans-serif;font-stretch:125%;letter-spacing:-.02em;margin:0 0 28px;text-wrap:balance}
h2{font:700 1.25rem/1.25 "Archivo","Helvetica Neue",Arial,sans-serif;font-stretch:112%;margin:40px 0 10px}
p,li{text-wrap:pretty}p{margin:0 0 14px}ul{padding-left:1.2em;margin:0 0 14px}
a{color:var(--heather);text-underline-offset:3px}
:focus-visible{outline:2px solid var(--heather);outline-offset:3px}
.home{display:inline-block;margin-top:24px;font:500 .8125rem/1 "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.06em;text-transform:uppercase;color:var(--ink);border:1px solid var(--ink);padding:14px 20px;text-decoration:none}
.updated{font:500 .8125rem/1.5 "IBM Plex Mono",ui-monospace,monospace;color:var(--muted)}'''
def small_page(path,title,desc,body):
    page=f'''<!DOCTYPE html>
<html lang="en">
<head>
{HEAD_COMMON}
<title>{title}</title>
<meta name="description" content="{desc}">
<style>{SMALL_CSS}</style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
'''
    tmp='_source/build-tmp-'+path.split('/')[-1]+'.full.html';open(tmp,'w').write(page); finish(tmp,path)

small_page('404.html','Page not found · Kinmoor Studios','This page does not exist.','''<p class="eyebrow">Kinmoor Studios · 404</p>
<h1>This page isn't here.</h1>
<p>The address may have a typo, or the page may have moved.</p>
<a class="home" href="/">Back to Kinmoor Studios</a>''')

small_page('privacy.html','Privacy · Kinmoor Studios','How kinmoorstudios.com handles information.','''<p class="eyebrow">Kinmoor Studios · Privacy</p>
<h1>Privacy</h1>
<p class="updated">Last updated 24 October 2026</p>
<p>This notice covers kinmoorstudios.com, run by Kinmoor Studios, LLC. The short version: the site doesn't collect information about you.</p>
<h2>What the site doesn't do</h2>
<ul>
<li>It sets no cookies.</li>
<li>It runs no analytics, advertising, or tracking scripts, and loads nothing from other companies.</li>
<li>It has no forms that send information to us.</li>
</ul>
<h2>What stays in your browser</h2>
<p>If you choose light or dark mode, or pause the animation, your browser remembers that choice in its local storage so the site looks the same next time. It never leaves your device, and you can clear it in your browser's settings. The speed figures on the home page are measured in your browser and aren't sent anywhere.</p>
<h2>Hosting</h2>
<p>The site is hosted on GitHub Pages and delivered through Cloudflare. Like any web host, they receive technical details of each request, such as your IP address and browser type, to deliver the site and protect it from abuse. They handle that under their own privacy policies. We don't receive or use it.</p>
<h2>The store test</h2>
<p>If you use “Run the test”, the web address you type is sent directly from your browser to Google PageSpeed Insights, a Google service covered by Google's privacy policy. We don't see it.</p>
<h2>Email</h2>
<p>If you email hello@kinmoorstudios.com, we use your message only to reply and keep it only as long as the conversation needs. Ask at the same address and we'll delete it.</p>
<a class="home" href="/">Back to Kinmoor Studios</a>''')
print('built')
