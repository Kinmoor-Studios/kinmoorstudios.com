  /* ---------- Hero background: contour map, drifting colour, and travelling lights ----------
     All of it is drawn by kinHero(). Where the browser allows, kinHero runs in a background thread
     (a Web Worker drawing to OffscreenCanvas), so scrolling, taps and typing never wait for it.
     Older browsers run the same code on the page's own thread. */
  function kinHero(scope,isWorker){
    var cb,ci,cl,ca,bx,ix,lx,ax,W=0,H=0,DPR=1,LDPR=1,col=null,reduce=false,still=false,on=false,raf=0;
    var paths=[],lights=[],pal=[],aCols=[],aW=0,aH=0,T=30,lastT=0,lastLight=0,lastAtm=0,dirty=[];
    var workAcc=0,workN=0,lastReport=0,quality=0,winN=0,winSlow=0,calm=0;
    var rAF=(typeof requestAnimationFrame==='function')?function(f){return requestAnimationFrame(f)}:function(f){return setTimeout(function(){f(performance.now())},16)};
    var cAF=(typeof cancelAnimationFrame==='function')?function(h){cancelAnimationFrame(h)}:function(h){clearTimeout(h)};
    function post(m){scope.postMessage(m)}
    function hash(x,y){var h=Math.imul(x,374761393)+Math.imul(y,668265263)|0;h=Math.imul(h^(h>>>13),1274126177);return((h^(h>>>16))>>>0)/4294967295}
    function sm(t){return t*t*(3-2*t)}
    function ease(t){return t<=0?0:t>=1?1:t*t*(3-2*t)}
    function vn(x,y){var xi=Math.floor(x),yi=Math.floor(y),xf=x-xi,yf=y-yi,u=sm(xf),v=sm(yf);
      var a=hash(xi,yi),b=hash(xi+1,yi),c=hash(xi,yi+1),d=hash(xi+1,yi+1);return a+(b-a)*u+(c-a)*v+(a-b-c+d)*u*v}
    function field(x,y){return .6*vn(x/320,y/320)+.3*vn(x/150+17,y/150+5)+.1*vn(x/70+3,y/70+41)}
    function rgb(c){var m=/^#([0-9a-f]{6})$/i.exec(c||'');if(!m)return[0,0,0];var n=parseInt(m[1],16);return[n>>16&255,n>>8&255,n&255]}
    function rgba(v){var m=/rgba?\(([^)]+)\)/.exec(v||'');if(!m)return[0,0,0,0];var a=m[1].split(',').map(parseFloat);return[a[0],a[1],a[2],a.length>3?a[3]:1]}
    function key(x,y){return Math.round(x*8)*131072+Math.round(y*8)}

    /* Contours: computed once, drawn once. */
    function chainUp(seg){
      var n=seg.length/4,map=new Map(),used=new Uint8Array(n),out=[];
      function add(k,i){var a=map.get(k);if(a)a.push(i);else map.set(k,[i])}
      for(var i=0;i<n;i++){add(key(seg[4*i],seg[4*i+1]),i);add(key(seg[4*i+2],seg[4*i+3]),i)}
      function next(x,y){var a=map.get(key(x,y));if(a)for(var t=0;t<a.length;t++)if(!used[a[t]])return a[t];return -1}
      function grow(arr){for(;;){var x=arr[arr.length-2],y=arr[arr.length-1],j=next(x,y);if(j<0)return;used[j]=1;
        if(key(seg[4*j],seg[4*j+1])===key(x,y))arr.push(seg[4*j+2],seg[4*j+3]);else arr.push(seg[4*j],seg[4*j+1])}}
      for(var s0=0;s0<n;s0++){if(used[s0])continue;used[s0]=1;
        var head=[seg[4*s0+2],seg[4*s0+3]],tail=[seg[4*s0],seg[4*s0+1]];grow(head);grow(tail);
        var pts=[];for(var t=tail.length-2;t>=0;t-=2)pts.push(tail[t],tail[t+1]);for(t=0;t<head.length;t++)pts.push(head[t]);
        if(pts.length>=6)out.push(pts)}
      return out}
    function chaikin(p,it){for(var k=0;k<it;k++){var q=[p[0],p[1]];for(var i=0;i<p.length-2;i+=2){var x0=p[i],y0=p[i+1],x1=p[i+2],y1=p[i+3];
      q.push(.75*x0+.25*x1,.75*y0+.25*y1,.25*x0+.75*x1,.25*y0+.75*y1)}q.push(p[p.length-2],p[p.length-1]);p=q}return p}
    function resample(p,step){var out=[p[0],p[1]],carry=0;
      for(var i=2;i<p.length;i+=2){var x0=p[i-2],y0=p[i-1],dx=p[i]-x0,dy=p[i+1]-y0,len=Math.hypot(dx,dy),d=step-carry;
        while(d<=len){out.push(x0+dx*d/len,y0+dy*d/len);d+=step}carry=len-(d-step)}
      var a=new Float32Array(out);return{p:a,n:a.length/2,step:step,t:(a.length/2-1)*step}}
    function at(c,d){d=c.closed?((d%c.t)+c.t)%c.t:Math.max(0,Math.min(c.t,d));var f=d/c.step,i=Math.min(c.n-2,Math.floor(f)),u=f-i;
      return[c.p[2*i]+(c.p[2*i+2]-c.p[2*i])*u,c.p[2*i+1]+(c.p[2*i+3]-c.p[2*i+1])*u]}
    var CASES={1:[3,2],2:[2,1],3:[3,1],4:[0,1],5:[0,1,3,2],6:[0,2],7:[3,0],8:[3,0],9:[0,2],10:[3,0,2,1],11:[0,1],12:[3,1],13:[2,1],14:[3,2]};
    function fadeEdges(c,top){c.save();c.shadowBlur=0;c.globalCompositeOperation='destination-in';var g=c.createLinearGradient(0,0,0,c.canvas.height/(c===ax?1:DPR));
      if(top){g.addColorStop(0,'rgba(0,0,0,0)');g.addColorStop(.22,'rgba(0,0,0,1)')}else g.addColorStop(0,'rgba(0,0,0,1)');
      g.addColorStop(.55,'rgba(0,0,0,1)');g.addColorStop(1,'rgba(0,0,0,0)');c.fillStyle=g;c.fillRect(0,0,c.canvas.width,c.canvas.height);c.restore()}
    function drawContours(){
      if(!W||!H)return;
      var s=9,nx=Math.ceil(W/s)+1,ny=Math.ceil(H/s)+1,f=new Float32Array(nx*ny),j,i,E=[0,0,0,0,0,0,0,0];
      for(j=0;j<ny;j++)for(i=0;i<nx;i++)f[j*nx+i]=field(i*s+40,j*s+90);
      bx.clearRect(0,0,W,H);ix.clearRect(0,0,W,H);
      bx.strokeStyle=col.contour;bx.lineWidth=.9;bx.lineCap=bx.lineJoin='round';
      ix.strokeStyle=col.strong;ix.lineWidth=1.4;ix.lineCap=ix.lineJoin='round';ix.shadowColor=col.glow;ix.shadowBlur=5;
      paths=[];
      for(var k=0,L=.22;L<.8;L+=.035,k++){
        var seg=[];
        for(j=0;j<ny-1;j++)for(i=0;i<nx-1;i++){
          var a=f[j*nx+i],b=f[j*nx+i+1],c=f[(j+1)*nx+i+1],d=f[(j+1)*nx+i];
          var idx=(a>L?8:0)|(b>L?4:0)|(c>L?2:0)|(d>L?1:0);if(idx===0||idx===15)continue;
          var x0=i*s,y0=j*s;
          E[0]=x0+s*(L-a)/(b-a);E[1]=y0;E[2]=x0+s;E[3]=y0+s*(L-b)/(c-b);E[4]=x0+s*(L-d)/(c-d);E[5]=y0+s;E[6]=x0;E[7]=y0+s*(L-a)/(d-a);
          var cs=CASES[idx];for(var q=0;q<cs.length;q+=2)seg.push(E[2*cs[q]],E[2*cs[q]+1],E[2*cs[q+1]],E[2*cs[q+1]+1]);
        }
        var isIdx=k%4===0,ctx=isIdx?ix:bx,lines=chainUp(seg);
        ctx.beginPath();
        for(var m=0;m<lines.length;m++){var p=chaikin(lines[m],3);ctx.moveTo(p[0],p[1]);for(var r=2;r<p.length;r+=2)ctx.lineTo(p[r],p[r+1]);
          if(isIdx&&!reduce){var rs=resample(p,2);rs.closed=Math.hypot(p[0]-p[p.length-2],p[1]-p[p.length-1])<3;if(rs.t>260)paths.push(rs)}}
        ctx.stroke();
      }
      fadeEdges(bx,false);fadeEdges(ix,false);
    }

    /* Colour fields: painted into a canvas one sixth the hero's size, which the browser scales up. */
    var FIELDS=[
      {c:1,x:.12,y:.10,r:.42,ax:.08,ay:.10,px:86,py:70,p:0,o:0},
      {c:0,x:.58,y:.30,r:.38,ax:.10,ay:.12,px:102,py:78,p:0,o:1.7},
      {c:3,x:.88,y:.05,r:.36,ax:.07,ay:.12,px:74,py:94,p:0,o:3.1},
      {c:2,x:.30,y:.70,r:.34,ax:.12,ay:.08,px:110,py:84,p:0,o:4.4},
      {c:5,x:.38,y:.18,r:.40,ax:.10,ay:.08,px:90,py:66,p:76,o:.9},
      {c:4,x:.74,y:.45,r:.34,ax:.10,ay:.07,px:82,py:98,p:92,o:2.6},
      {c:6,x:.92,y:.52,r:.30,ax:.08,ay:.10,px:106,py:72,p:104,o:5.2}];
    function paintAtmos(t){
      var TAU=6.2832;ax.clearRect(0,0,aW,aH);
      for(var i=0;i<FIELDS.length;i++){var f=FIELDS[i],c=aCols[f.c],k=c[3]*.6;
        if(f.p)k*=.5-.5*Math.cos(TAU*t/f.p+f.o);if(k<.004)continue;
        var x=(f.x+f.ax*Math.sin(TAU*t/f.px+f.o))*aW,y=(f.y+f.ay*Math.sin(TAU*t/f.py+f.o*1.3))*aH,rad=f.r*aW*(1+.08*Math.sin(TAU*t/(f.px*1.7)+f.o));
        var g=ax.createRadialGradient(x,y,0,x,y,rad),s=c[0]+','+c[1]+','+c[2];
        g.addColorStop(0,'rgba('+s+','+k+')');g.addColorStop(.25,'rgba('+s+','+(k*.82)+')');g.addColorStop(.6,'rgba('+s+','+(k*.32)+')');g.addColorStop(1,'rgba('+s+',0)');
        ax.fillStyle=g;ax.fillRect(0,0,aW,aH)}
      fadeEdges(ax,true)}

    /* Lights: one per line, each blending between palette colours now and then. */
    function pick(){var tot=0,i,free=[];for(i=0;i<paths.length;i++)if(!paths[i].busy){free.push(paths[i]);tot+=paths[i].t}
      if(!free.length)return null;var r=Math.random()*tot;for(i=0;i<free.length;i++){r-=free[i].t;if(r<=0)return free[i]}return free[free.length-1]}
    function spawn(Lt){if(Lt.c)Lt.c.busy=false;var c=pick();if(!c){Lt.c=null;return}c.busy=true;Lt.c=c;Lt.dir=Math.random()<.5?1:-1;Lt.v=18+Math.random()*18;Lt.trail=70+Math.random()*50;
      Lt.s=Lt.trail+Math.random()*Math.max(1,c.t-2*Lt.trail);Lt.run=220+Math.random()*380;Lt.age=0;
      if(Lt.to===undefined){Lt.from=Lt.to=Math.floor(Math.random()*4);Lt.k=1;Lt.next=3+Math.random()*6}}
    function lightColour(Lt,dt){Lt.next-=dt;if(Lt.next<=0&&Lt.k>=1){Lt.from=Lt.to;do{Lt.to=Math.floor(Math.random()*pal.length)}while(Lt.to===Lt.from&&pal.length>1);Lt.k=0;Lt.next=4+Math.random()*6}
      Lt.k=Math.min(1,Lt.k+dt/2.4);var e=ease(Lt.k),A=pal[Lt.from]||[0,0,0],B=pal[Lt.to]||A;
      return Math.round(A[0]+(B[0]-A[0])*e)+','+Math.round(A[1]+(B[1]-A[1])*e)+','+Math.round(A[2]+(B[2]-A[2])*e)}
    function seedLights(){var cap=quality>=2?3:6,n=Math.min(paths.length,Math.round(Math.min(cap,Math.max(3,W/240))));
      paths.forEach(function(p){p.busy=false});lights=[];for(var z=0;z<n;z++){var Lt={};spawn(Lt);Lt.age=-z*1.6-Math.random()*1.2;lights.push(Lt)}}
    // Only the patches the lights touched last frame are cleared, instead of the whole hero.
    function stepLights(dt){
      for(var d=0;d<dirty.length;d++){var r=dirty[d];lx.clearRect(r[0],r[1],r[2],r[3])}
      dirty=[];
      for(var i=0;i<lights.length;i++){
        var Lt=lights[i];Lt.age+=dt;if(Lt.age<0)continue;
        if(!Lt.c){spawn(Lt);if(!Lt.c)continue}
        Lt.s+=Lt.dir*Lt.v*dt;Lt.run-=Lt.v*dt;
        var toEnd=Lt.c.closed?Infinity:(Lt.dir>0?Lt.c.t-Lt.s:Lt.s),left=Math.min(toEnd,Lt.run);
        if(left<=0){spawn(Lt);continue}
        var hp=at(Lt.c,Lt.s),lc=lightColour(Lt,dt);
        var a=ease(Lt.age/2)*ease(left/90)*ease((H*.9-hp[1])/(H*.35));
        if(a<=.005)continue;
        var tailD=Lt.s-Lt.dir*Lt.trail,tp=at(Lt.c,tailD),c=Lt.c,x0=hp[0],y0=hp[1],x1=hp[0],y1=hp[1];
        var g=lx.createLinearGradient(tp[0],tp[1],hp[0],hp[1]);
        g.addColorStop(0,'rgba('+lc+',0)');g.addColorStop(.55,'rgba('+lc+','+(.16*a).toFixed(3)+')');g.addColorStop(1,'rgba('+lc+','+(.5*a).toFixed(3)+')');
        lx.strokeStyle=g;lx.lineWidth=1.3;lx.beginPath();lx.moveTo(tp[0],tp[1]);
        for(var dd=c.step;dd<Lt.trail;dd+=c.step){var pp=at(c,tailD+Lt.dir*dd);lx.lineTo(pp[0],pp[1]);
          if(pp[0]<x0)x0=pp[0];if(pp[0]>x1)x1=pp[0];if(pp[1]<y0)y0=pp[1];if(pp[1]>y1)y1=pp[1]}
        lx.lineTo(hp[0],hp[1]);lx.stroke();
        var hg=lx.createRadialGradient(hp[0],hp[1],0,hp[0],hp[1],10),ha=a*.8;
        hg.addColorStop(0,'rgba('+lc+','+ha.toFixed(3)+')');hg.addColorStop(.1,'rgba('+lc+','+(ha*.75).toFixed(3)+')');hg.addColorStop(.3,'rgba('+lc+','+(ha*.22).toFixed(3)+')');hg.addColorStop(.6,'rgba('+lc+','+(ha*.06).toFixed(3)+')');hg.addColorStop(1,'rgba('+lc+',0)');
        lx.fillStyle=hg;lx.fillRect(hp[0]-10,hp[1]-10,20,20);
        dirty.push([Math.floor(x0-12),Math.floor(y0-12),Math.ceil(x1-x0+24),Math.ceil(y1-y0+24)]);
      }
    }
    function clearLights(){if(lx){lx.clearRect(0,0,W,H)}dirty=[]}

    /* Quality governor: if this device keeps missing frames, lower the cost; when it recovers, restore it.
       Level 1 draws the lights at standard resolution and the colour 20 times a second; level 2 also halves the lights' update rate and count. */
    function setQuality(q){if(q===quality)return;quality=q;LDPR=quality>=1?1:DPR;cl.width=Math.max(1,Math.round(W*LDPR));cl.height=Math.max(1,Math.round(H*LDPR));
      lx.setTransform(LDPR,0,0,LDPR,0,0);lx.lineCap=lx.lineJoin='round';dirty=[];if(quality>=2&&lights.length>3)lights.length=3;post({type:'quality',q:quality})}
    function govern(interval){winN++;if(interval>26)winSlow++;
      if(winN>=90){var share=winSlow/winN;
        if(share>.25&&quality<2){setQuality(quality+1);calm=0}
        else if(share<.03&&quality>0){if(++calm>=6){setQuality(quality-1);if(quality<2&&lights.length<3)seedLights();calm=0}}else calm=0;
        winN=0;winSlow=0}}

    function frame(now){raf=0;if(!on)return;
      var interval=lastT?now-lastT:0;lastT=now;if(interval)govern(interval);
      var w0=performance.now();
      // Frame pacing: the lights move a few pixels a second, so they update at most 60 times a second (30 at level 2), even on 120 Hz screens.
      var gap=quality>=2?32:15.5;
      if(!still&&now-lastLight>=gap){var dt=lastLight?Math.min(1/20,(now-lastLight)/1000):0;lastLight=now;T+=dt;stepLights(dt)}
      if(now-lastAtm>=(quality>=1?48:32)){if(!lastLight)T+=lastAtm?(now-lastAtm)/1000:0;lastAtm=now;paintAtmos(T)}
      workAcc+=performance.now()-w0;workN++;
      if(now-lastReport>=1000&&workN){post({type:'stats',work:workAcc/workN,q:quality});workAcc=0;workN=0;lastReport=now}
      raf=rAF(frame)}
    function sizeAll(z){W=z.W;H=z.H;DPR=z.DPR;LDPR=quality>=1?1:DPR;
      [[cb,DPR],[ci,DPR],[cl,LDPR]].forEach(function(e){e[0].width=Math.max(1,Math.round(W*e[1]));e[0].height=Math.max(1,Math.round(H*e[1]))});
      bx.setTransform(DPR,0,0,DPR,0,0);ix.setTransform(DPR,0,0,DPR,0,0);lx.setTransform(LDPR,0,0,LDPR,0,0);lx.lineCap=lx.lineJoin='round';
      aW=Math.max(2,Math.round(W/6));aH=Math.max(2,Math.round(H/6));ca.width=aW;ca.height=aH;dirty=[]}
    function setColours(c){col=c;pal=c.tr.map(rgb);aCols=c.atm.map(rgba)}
    function handle(m){
      if(m.type==='init'){cb=m.base;ci=m.idx;cl=m.lit;ca=m.atm;bx=cb.getContext('2d');ix=ci.getContext('2d');lx=cl.getContext('2d');ax=ca.getContext('2d');
        reduce=!!m.reduce;still=!!m.still;setColours(m.col);sizeAll(m.size);drawContours();paintAtmos(T);if(!reduce)seedLights();post({type:'ready'})}
      else if(m.type==='size'){sizeAll(m.size);drawContours();paintAtmos(T);if(!reduce)seedLights()}
      else if(m.type==='col'){setColours(m.col);drawContours();paintAtmos(T);clearLights()}
      else if(m.type==='still'){still=!!m.on;if(still)clearLights();lastLight=0}
      else if(m.type==='run'){var want=!!m.on&&!reduce;if(want&&!on){on=true;lastT=0;lastLight=0;lastAtm=0;raf=rAF(frame)}else if(!want&&on){on=false;if(raf)cAF(raf);raf=0}}
    }
    if(isWorker)scope.onmessage=function(e){handle(e.data)};
    return handle;
  }

  /* ---------- Page side: starts kinHero, keeps it in step with the page ---------- */
  var hero=document.querySelector('.hero'),stack=document.querySelector('.contour-stack'),atmosEl=document.querySelector('.atmos');
  var reduce=false; try{reduce=matchMedia('(prefers-reduced-motion: reduce)').matches}catch(e){}
  function tok(n){return getComputedStyle(root).getPropertyValue(n).trim()}
  function colours(){return{contour:tok('--contour'),strong:tok('--contour-strong'),glow:tok('--glow'),
    tr:['--tr1','--tr2','--tr3','--tr4'].map(tok),atm:['--atm1','--atm2','--atm3','--atm4','--atm5','--atm6','--atm7'].map(tok)}}
  function measure(){var r=hero.getBoundingClientRect();return{W:r.width,H:r.height,DPR:Math.min(window.devicePixelRatio||1,2)}}
  var worker=null,send=null,ready=false,onScreen=true,offThread=false,dead=false,quality=0;
  // A visible control to stop the background (WCAG 2.2.2), remembered for the next visit.
  var still=false,mbtn=document.getElementById('motion');try{still=localStorage.getItem('kinmoor-motion')==='paused'}catch(e){}
  function budgetText(){return 'Budget 2 ms'+(offThread?' · own thread':'')}
  function onStats(m){
    if(m.type==='ready'){ready=true;hero.classList.add('drawn');begin()}
    else if(m.type==='quality'){quality=m.q;hero.dataset.quality=m.q}
    else if(m.type==='stats'&&!still&&!reduce){set('m-anim',m.work.toFixed(2)+' ms',m.work<=2?'ok':'over',budgetText())}}
  function showMotion(){mbtn.setAttribute('aria-pressed',still?'true':'false');mbtn.textContent=still?'Play animation':'Pause animation';hero.classList.toggle('still',still);
    if(still)set('m-anim','0.00 ms','info','Paused')}
  if(reduce){mbtn.hidden=true;set('m-anim','Off','info','Reduced motion is on')}else showMotion();
  function boot(){
    if(dead)return;
    var cvB=document.getElementById('contours'),cvI=document.getElementById('contours-index'),cvL=document.getElementById('contours-lights'),cvA=document.getElementById('atmos-cv');
    var msg={type:'init',size:measure(),col:colours(),reduce:reduce,still:still};
    if(cvB.transferControlToOffscreen&&window.Worker&&window.OffscreenCanvas){
      try{
        var url=URL.createObjectURL(new Blob(['('+kinHero.toString()+')(self,true)'],{type:'text/javascript'}));
        worker=new Worker(url);worker.onmessage=function(e){onStats(e.data)};
        msg.base=cvB.transferControlToOffscreen();msg.idx=cvI.transferControlToOffscreen();msg.lit=cvL.transferControlToOffscreen();msg.atm=cvA.transferControlToOffscreen();
        offThread=true;worker.postMessage(msg,[msg.base,msg.idx,msg.lit,msg.atm]);
        send=function(m){if(worker)worker.postMessage(m)};
      }catch(e){if(worker)worker.terminate();worker=null;offThread=false}
    }
    if(!worker){var h=kinHero({postMessage:onStats},false);send=h;msg.base=cvB;msg.idx=cvI;msg.lit=cvL;msg.atm=cvA;h(msg)}
    hero.dataset.renderer=offThread?'worker':'main';
  }
  function start(){if(dead||!ready||still||reduce||!onScreen||document.hidden)return;send({type:'run',on:true})}
  function stop(){if(send)send({type:'run',on:false})}
  mbtn.onclick=function(){still=!still;try{localStorage.setItem('kinmoor-motion',still?'paused':'playing')}catch(e){}
    showMotion();if(send)send({type:'still',on:still});if(still)stop();else{set('m-anim','…','',budgetText());start()}};
  // A live update may start this script again: the old thread is stopped and its canvases swapped for fresh ones.
  function kill(){stop();dead=true;if(worker){worker.terminate();worker=null;
    ['contours','contours-index','contours-lights','atmos-cv'].forEach(function(id){var o=document.getElementById(id);if(!o)return;var n=document.createElement('canvas');n.id=id;n.className=o.className;o.replaceWith(n)})}}
  var idle=window.requestIdleCallback||function(fn){return setTimeout(fn,60)};
  idle(boot);
  // The lights start only after the page has finished loading, so they never compete with it.
  var begun=false;function begin(){if(begun)return;begun=true;var go=function(){setTimeout(function(){idle(start)},700)};if(document.readyState==='complete')go();else addEventListener('load',go,sig)}
  try{(obs[obs.length]=new IntersectionObserver(function(es){onScreen=es[es.length-1].isIntersecting;if(!ready)return;onScreen?start():stop()})).observe(hero)}catch(e){}
  document.addEventListener('visibilitychange',function(){if(!ready)return;document.hidden?stop():start()},sig);
  addEventListener('pageshow',function(){if(ready)start()},sig);
  // On a theme change, fade the map out, redraw it in the new colours, and fade it back in.
  var swapT;
  function themeRedraw(){if(!ready)return;if(reduce){send({type:'col',col:colours()});return}
    stack.classList.add('fading');atmosEl.classList.add('fading');clearTimeout(swapT);
    swapT=setTimeout(function(){send({type:'col',col:colours()});setTimeout(function(){stack.classList.remove('fading');atmosEl.classList.remove('fading')},60)},230)}
  var rt,lastW=0; addEventListener('resize',function(){clearTimeout(rt);rt=setTimeout(function(){var w=hero.clientWidth;if(ready&&w!==lastW){lastW=w;send({type:'size',size:measure()})}},200)},sig);
  try{matchMedia('(prefers-color-scheme: dark)').addEventListener('change',themeRedraw,sig)}catch(e){}
  try{(obs[obs.length]=new MutationObserver(themeRedraw)).observe(root,{attributes:true,attributeFilter:['data-theme']})}catch(e){}

