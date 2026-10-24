# Scroll benchmark: records the time between frames while the page is scrolled down and back up with the mouse wheel.
import sys, statistics
from playwright.sync_api import sync_playwright
pages=sys.argv[1:] or ['index.html']
REC="""()=>{window.__f=[];let p=0;function f(t){if(p)window.__f.push(t-p);p=t;if(!window.__stop)requestAnimationFrame(f)}requestAnimationFrame(f);
 window.__lt=0;try{new PerformanceObserver(l=>l.getEntries().forEach(e=>window.__lt+=e.duration)).observe({type:'longtask'})}catch(e){}}"""
with sync_playwright() as p:
    b=p.chromium.launch()
    res={}
    for rnd in range(int(__import__("os").environ.get("ROUNDS","3"))):
        for f in pages:
            pg=b.new_page(viewport={'width':1366,'height':900},color_scheme='dark',device_scale_factor=2)
            pg.goto('http://127.0.0.1:8766/'+f); pg.wait_for_timeout(3500)
            pg.mouse.move(400,450); pg.evaluate(REC)
            for i in range(40): pg.mouse.wheel(0,120); pg.wait_for_timeout(45)
            for i in range(40): pg.mouse.wheel(0,-120); pg.wait_for_timeout(45)
            pg.wait_for_timeout(300); fr=pg.evaluate("window.__stop=1,window.__f"); lt=pg.evaluate("window.__lt")
            res.setdefault(f,[]).append((fr,lt)); pg.close()
    for f,runs in res.items():
        allf=[x for fr,_ in runs for x in fr]; allf.sort()
        p95=allf[int(len(allf)*.95)]; slow=sum(1 for x in allf if x>20)/len(allf)*100
        print(f"{f:28s} frames {len(allf):4d}  median {statistics.median(allf):5.1f} ms  p95 {p95:5.1f}  max {max(allf):6.1f}  >20ms {slow:4.1f}%  long tasks {sum(lt for _,lt in runs)/len(runs):5.0f} ms")
    b.close()
