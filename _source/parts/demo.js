  /* ---------- Frame-time graphs ---------- */
  var gcol={};
  function graphColours(){gcol={ink:tok('--muted'),rule:tok('--rule'),ok:tok('--lichen'),over:tok('--warn'),area:tok('--heather')}}
  graphColours();
  try{(obs[obs.length]=new MutationObserver(graphColours)).observe(root,{attributes:true,attributeFilter:['data-theme']})}catch(e){}
  try{matchMedia('(prefers-color-scheme: dark)').addEventListener('change',graphColours,sig)}catch(e){}
  // Draws frame times as a line (green under the 60 fps line, amber over it), with script time per frame as a shaded area underneath.
  function drawGraph(cv,frames,work,maxMs,label){
    var dpr=Math.min(window.devicePixelRatio||1,2),w=cv.clientWidth,h=cv.clientHeight;if(!w||!h)return;
    if(cv.width!==Math.round(w*dpr)||cv.height!==Math.round(h*dpr)){cv.width=Math.round(w*dpr);cv.height=Math.round(h*dpr)}
    var c=cv.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,w,h);
    var n=frames.length,cap=cv._cap||240,step=w/(cap-1),y=function(ms){return h-2-Math.min(ms,maxMs)/maxMs*(h-4)};
    var ry=Math.round(y(16.7))+.5;c.strokeStyle=gcol.rule;c.lineWidth=1;c.setLineDash([3,3]);c.beginPath();c.moveTo(0,ry);c.lineTo(w,ry);c.stroke();c.setLineDash([]);
    if(label){c.fillStyle=gcol.ink;c.font='500 10px "IBM Plex Mono","Plex Mono Fallback",monospace';c.textBaseline='bottom';c.fillText('60 fps',4,ry-2)}
    if(!n)return;var x0=w-(n-1)*step;
    if(work&&work.length){c.globalAlpha=.28;c.fillStyle=gcol.area;c.beginPath();c.moveTo(x0,h);for(var i=0;i<work.length;i++)c.lineTo(x0+i*step,y(work[i]));c.lineTo(x0+(work.length-1)*step,h);c.closePath();c.fill();c.globalAlpha=1}
    c.lineWidth=1.4;c.lineJoin='round';
    // Two strokes in total, one per colour, rather than one per segment.
    var okP=new Path2D(),overP=new Path2D();
    for(var j=1;j<n;j++){var P=(frames[j]>20||frames[j-1]>20)?overP:okP;P.moveTo(x0+(j-1)*step,y(frames[j-1]));P.lineTo(x0+j*step,y(frames[j]))}
    c.strokeStyle=gcol.ok;c.stroke(okP);c.strokeStyle=gcol.over;c.stroke(overP);
  }
  function push(arr,v,cap){arr.push(v);if(arr.length>cap)arr.shift()}

  /* Readout graph: the hero animation's own frames, redrawn a few times a second. */
  var sparkCv=document.getElementById('spark'),sparkF=[],sparkW=[],sparkN=0;if(sparkCv)sparkCv._cap=180;
  function pushFrame(interval,work){push(sparkF,interval,180);push(sparkW,work,180);if(++sparkN%10===0&&sparkCv)drawGraph(sparkCv,sparkF,sparkW,33,false)}

  /* ---------- Side-by-side test: the same dots, drawn the usual way and our way ---------- */
  var stage=document.getElementById('demo-stage'),dcv=document.getElementById('demo-canvas'),ddom=document.getElementById('demo-dom'),dgraph=document.getElementById('demo-graph');
  var dCount=document.getElementById('demo-count'),dCountOut=document.getElementById('demo-count-out'),dStatus=document.getElementById('demo-status');
  var bUsual=document.getElementById('demo-usual'),bOurs=document.getElementById('demo-ours'),bStop=document.getElementById('demo-stop');
  var sMed=document.getElementById('demo-med'),sSlow=document.getElementById('demo-slow'),sWork=document.getElementById('demo-work');
  var dMode=null,dRaf=0,dLast=0,dT0=0,N=+dCount.value,px,py,vx,vy,pc,dF=[],dW=[],dEls=[],dSprites=[],dOn=true;
  if(dgraph)dgraph._cap=240;
  function demoPalette(){return['--tr1','--tr2','--tr3','--tr4'].map(function(n){return tok(n)})}
  function seed(){var r=stage.getBoundingClientRect();px=new Float32Array(N);py=new Float32Array(N);vx=new Float32Array(N);vy=new Float32Array(N);pc=new Uint8Array(N);
    for(var i=0;i<N;i++){px[i]=Math.random()*r.width;py[i]=Math.random()*r.height;var a=Math.random()*6.283,s=30+Math.random()*60;vx[i]=Math.cos(a)*s;vy[i]=Math.sin(a)*s;pc[i]=i%4}}
  function move(dt,w,h){for(var i=0;i<N;i++){var x=px[i]+vx[i]*dt,y=py[i]+vy[i]*dt;if(x<0||x>w){vx[i]=-vx[i];x=x<0?0:w}if(y<0||y>h){vy[i]=-vy[i];y=y<0?0:h}px[i]=x;py[i]=y}}
  // Our way: one glow per colour painted once, then each dot is a single image copy into one canvas.
  function buildSprites(){var dpr=Math.min(window.devicePixelRatio||1,2),pal=demoPalette();dSprites=pal.map(function(col){var s=document.createElement('canvas'),z=Math.round(28*dpr);s.width=s.height=z;
    var c=s.getContext('2d'),g=c.createRadialGradient(z/2,z/2,0,z/2,z/2,z/2);g.addColorStop(0,col);g.addColorStop(.18,col);g.addColorStop(.4,col+'55');g.addColorStop(1,col+'00');c.fillStyle=g;c.fillRect(0,0,z,z);return s})}
  // The usual way: one element per dot with a live glow, moved by its page position, measuring the page after every move.
  function buildDom(){var pal=demoPalette(),f=document.createDocumentFragment();dEls=[];
    for(var i=0;i<N;i++){var e=document.createElement('i');e.className='dot';e.style.background=pal[pc[i]];e.style.boxShadow='0 0 10px 4px '+pal[pc[i]]+'88';f.appendChild(e);dEls.push(e)}
    ddom.textContent='';ddom.appendChild(f)}
  function stat(){if(!dF.length)return;var s=dF.slice().sort(function(a,b){return a-b}),med=s[s.length>>1],slow=0,wk=0;for(var i=0;i<dF.length;i++)if(dF[i]>20)slow++;for(i=0;i<dW.length;i++)wk+=dW[i];
    sMed.textContent=med.toFixed(1)+' ms';sSlow.textContent=Math.round(slow/dF.length*100)+'%';sWork.textContent=(wk/dW.length).toFixed(2)+' ms';
    sMed.parentNode.dataset.state=med>20?'over':'ok';sSlow.parentNode.dataset.state=slow/dF.length>.05?'over':'ok';sWork.parentNode.dataset.state=wk/dW.length>8?'over':'ok'}
  function demoFrame(t){dRaf=0;if(!dMode)return;
    var r=stage.getBoundingClientRect(),w=r.width,h=r.height,dt=dLast?Math.min(.05,(t-dLast)/1000):0;if(dLast)push(dF,t-dLast,240);dLast=t;
    var w0=performance.now();move(dt,w,h);
    if(dMode==='usual'){for(var i=0;i<N;i++){var e=dEls[i];e.style.left=px[i]+'px';e.style.top=py[i]+'px';e.getBoundingClientRect()}}
    else{var dpr=Math.min(window.devicePixelRatio||1,2);if(dcv.width!==Math.round(w*dpr)){dcv.width=Math.round(w*dpr);dcv.height=Math.round(h*dpr)}
      var c=dcv.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,w,h);for(var j=0;j<N;j++)c.drawImage(dSprites[pc[j]],px[j]-14,py[j]-14,28,28)}
    var work=performance.now()-w0;push(dW,work,240);drawGraph(dgraph,dF,dW,50,true);if(dF.length%10===0)stat();
    if(dMode==='usual'){var el=(t-dT0)/1000;
      if(work>800||el>10){demoStop(work>800?'Stopped: a single frame took '+Math.round(work)+' ms.':'Stopped after 10 seconds so it doesn’t slow the rest of the page.');return}
      dStatus.textContent='Running the usual way · stops by itself in '+Math.max(0,Math.ceil(10-el))+' s'}
    dRaf=requestAnimationFrame(demoFrame)}
  function demoRun(mode){demoStop('');dMode=mode;N=+dCount.value;seed();dF=[];dW=[];dLast=0;dT0=performance.now();
    stage.dataset.mode=mode;bUsual.setAttribute('aria-pressed',mode==='usual');bOurs.setAttribute('aria-pressed',mode==='ours');bStop.disabled=false;
    if(mode==='usual'){buildDom();dcv.getContext('2d').clearRect(0,0,dcv.width,dcv.height)}else{ddom.textContent='';dEls=[];buildSprites();dStatus.textContent='Running our way · press Stop when you’ve seen enough'}
    stat();if(dOn)dRaf=requestAnimationFrame(demoFrame)}
  function demoStop(msg){if(dRaf)cancelAnimationFrame(dRaf);dRaf=0;if(dMode)stat();dMode=null;bUsual.setAttribute('aria-pressed','false');bOurs.setAttribute('aria-pressed','false');bStop.disabled=true;
    ddom.textContent='';dEls=[];if(msg!=='')dStatus.textContent=msg||'Stopped.'}
  bUsual.onclick=function(){demoRun('usual')};bOurs.onclick=function(){demoRun('ours')};bStop.onclick=function(){demoStop()};
  dCount.addEventListener('input',function(){dCountOut.textContent=dCount.value;if(dMode)demoRun(dMode)},sig);
  try{(obs[obs.length]=new IntersectionObserver(function(es){dOn=es[es.length-1].isIntersecting;if(!dOn&&dMode)demoStop('Stopped when you scrolled away.')})).observe(stage)}catch(e){}
  document.addEventListener('visibilitychange',function(){if(document.hidden&&dMode)demoStop('Stopped while the tab was in the background.')},sig);
  drawGraph(dgraph,[],[],50,true);
