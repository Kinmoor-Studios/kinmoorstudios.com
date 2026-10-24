// Minifies the inline <style> and <script> blocks of one HTML file, and trims indentation between tags.
const fs=require('fs'),{minify}=require('terser'),csso=require('csso');
(async()=>{
  const [inp,out]=process.argv.slice(2);let h=fs.readFileSync(inp,'utf8');
  h=h.replace(/<style>([\s\S]*?)<\/style>/g,(m,css)=>'<style>'+csso.minify(css).css+'</style>');
  const parts=[];let last=0;const re=/<script>([\s\S]*?)<\/script>/g;let m;
  while((m=re.exec(h))){parts.push(h.slice(last,m.index));const r=await minify(m[1],{compress:{passes:2},mangle:true,format:{comments:false}});parts.push('<script>'+r.code+'</script>');last=re.lastIndex}
  parts.push(h.slice(last));h=parts.join('');
  h=h.replace(/\n[ \t]+/g,'\n');
  fs.writeFileSync(out,h);
})().catch(e=>{console.error(e);process.exit(1)});
