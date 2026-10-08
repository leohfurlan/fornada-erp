/* Reproducible conversion of the approved artwork to scalable brand assets. */
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('C:/Users/Leonardo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root = path.resolve(__dirname, '..');
const color = { primary:'#D95D39', ink:'#2E2824', cream:'#FFF6EE', white:'#FFFFFF' };
const word = JSON.parse(fs.readFileSync(path.join(__dirname,'wordmark-outlines.json'),'utf8'));
const num = v => Number(v.toFixed(3));
const escape = text => text.replaceAll('&','&amp;').replaceAll('<','&lt;');

function componentBounds(pixels,width) {
  let x0=Infinity,y0=Infinity,x1=0,y1=0;
  for(const i of pixels){const x=i%width,y=Math.floor(i/width);x0=Math.min(x0,x);x1=Math.max(x1,x);y0=Math.min(y0,y);y1=Math.max(y1,y);}
  return [x0,y0,x1+1,y1+1];
}
function fitEllipse(points,cx,rx) {
  let a=0,b=0,c=0,d=0;
  for(const [x,y]of points){const s=Math.sqrt(Math.max(0,1-((x-cx)/rx)**2));a+=s;b+=s*s;c+=y;d+=s*y;}
  const n=points.length,den=n*b-a*a,cy=(c*b-a*d)/den,ry=-(n*d-a*c)/den;
  return {cx,cy,rx,ry};
}
function fitApprovedForms(kept,width,height) {
  const arch=componentBounds(kept[0],width),tray=componentBounds(kept[1],width),m=new Uint8Array(width*height);
  for(const i of kept[0])m[i]=1;
  const outer=[],inner=[],w=arch[2]-arch[0];
  for(let x=Math.ceil(arch[0]+w*.08);x<arch[2]-w*.08;x++){
    let y=arch[1];while(y<arch[3]&&!m[y*width+x])y++;
    outer.push([x,y]);
    if(x>arch[0]+w*.25&&x<arch[0]+w*.75){while(y<arch[3]&&m[y*width+x])y++;inner.push([x,y]);}
  }
  const cx=(arch[0]+arch[2])/2,o=fitEllipse(outer,cx,w/2),row=Math.round(o.cy);
  let il=arch[0];while(il<cx&&!m[row*width+il])il++;while(il<cx&&m[row*width+il])il++;
  let ir=arch[2]-1;while(ir>cx&&!m[row*width+ir])ir--;while(ir>cx&&m[row*width+ir])ir--;ir++;
  const i=fitEllipse(inner,(il+ir)/2,(ir-il)/2),t=o.rx-i.rx,bottom=arch[3],corner=t*.44,bendWidth=t*.70;
  const xl=arch[0],xr=arch[2],yb=bottom-corner,k=.5522847498;
  const archPath=`M${num(xl)} ${num(o.cy)}A${num(o.rx)} ${num(o.ry)} 0 0 1 ${num(xr)} ${num(o.cy)}L${num(xr)} ${num(yb)}C${num(xr)} ${num(yb+corner*k)} ${num(xr-corner+corner*k)} ${num(bottom)} ${num(xr-corner)} ${num(bottom)}L${num(ir-bendWidth)} ${num(bottom)}C${num(ir-bendWidth*.45)} ${num(bottom-3)} ${num(ir)} ${num(yb+corner*.55)} ${num(ir)} ${num(yb)}L${num(ir)} ${num(i.cy)}A${num(i.rx)} ${num(i.ry)} 0 0 0 ${num(il)} ${num(i.cy)}L${num(il)} ${num(yb)}C${num(il)} ${num(yb+corner*.55)} ${num(il+bendWidth*.45)} ${num(bottom-3)} ${num(il+bendWidth)} ${num(bottom)}L${num(xl+corner)} ${num(bottom)}C${num(xl+corner-corner*k)} ${num(bottom)} ${num(xl)} ${num(yb+corner*k)} ${num(xl)} ${num(yb)}Z`;
  const [tx0,ty0,tx1,ty1]=tray,tr=(ty1-ty0)/2;
  const trayPath=`M${num(tx0+tr)} ${ty0}H${num(tx1-tr)}A${num(tr)} ${num(tr)} 0 0 1 ${num(tx1-tr)} ${ty1}H${num(tx0+tr)}A${num(tr)} ${num(tr)} 0 0 1 ${num(tx0+tr)} ${ty0}Z`;
  return {paths:[archPath,trayPath],bounds:[xl,o.cy-o.ry,xr,bottom],fit:{outerArc:o,innerArc:i,corner,trayBounds:tray}};
}
async function trace() {
  const {data,info}=await sharp(path.join(__dirname,'referencia-aprovada.png')).ensureAlpha().raw().toBuffer({resolveWithObject:true});
  const {width,height}=info,length=width*height,seen=new Uint8Array(length),mask=new Uint8Array(length),queue=new Int32Array(length),components=[];
  const integral=new Uint32Array((width+1)*(height+1)),stride=width+1;
  for(let y=0;y<height;y++){let row=0;for(let x=0;x<width;x++){row+=data[(y*width+x)*4+3]>=128?1:0;integral[(y+1)*stride+x+1]=integral[y*stride+x+1]+row;}}
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){const xa=Math.max(0,x-4),xb=Math.min(width,x+5),ya=Math.max(0,y-4),yb=Math.min(height,y+5);const sum=integral[yb*stride+xb]-integral[ya*stride+xb]-integral[yb*stride+xa]+integral[ya*stride+xa];mask[y*width+x]=sum>=(xb-xa)*(yb-ya)/2?1:0;}
  for(let start=0;start<length;start++)if(mask[start]&&!seen[start]){
    let head=0,tail=0;queue[tail++]=start;seen[start]=1;const pixels=[];
    while(head<tail){const i=queue[head++];pixels.push(i);const x=i%width,y=Math.floor(i/width);for(const j of [x>0?i-1:-1,x<width-1?i+1:-1,y>0?i-width:-1,y<height-1?i+width:-1])if(j>=0&&mask[j]&&!seen[j]){seen[j]=1;queue[tail++]=j;}}
    if(pixels.length>100)components.push(pixels);
  }
  components.sort((a,b)=>b.length-a.length);
  if(components.length<2)throw Error('Expected separate arch and baking tray in the approved reference.');
  const kept=components.slice(0,2);
  const fitted=fitApprovedForms(kept,width,height);
  const geometry={source:'referencia-aprovada.png',method:'Two original alpha components; least-squares fit of the existing oven arcs, rounded footer transitions and capsule tray. Color standardized to #D95D39.',bounds:fitted.bounds,components:kept.map(p=>p.length),paths:fitted.paths,fit:fitted.fit};
  const rendered=await sharp(Buffer.from(svg(width,height,`<g fill="#000">${fitted.paths.map(d=>`<path d="${d}"/>`).join('')}</g>`,'Geometry verification'))).ensureAlpha().raw().toBuffer();
  let intersection=0,union=0;const original=new Uint8Array(length);for(const pixels of kept)for(const p of pixels)original[p]=1;
  for(let p=0;p<length;p++){const a=original[p],b=rendered[p*4+3]>=128?1:0;if(a&&b)intersection++;if(a||b)union++;}
  geometry.silhouetteIoU=intersection/union;
  if(geometry.silhouetteIoU<.95){console.log(JSON.stringify(fitted.fit));throw Error(`Geometry fidelity too low: ${geometry.silhouetteIoU}`);}
  fs.writeFileSync(path.join(__dirname,'symbol-geometry.json'),JSON.stringify(geometry,null,2));
  return geometry;
}
function svg(width,height,body,title) {return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escape(title)}"><title>${escape(title)}</title>${body}</svg>`;}
function mark(g,c,cx,cy,width) {
  const [x0,y0,x1,y1]=g.bounds,s=width/(x1-x0),tx=cx-(x0+x1)*s/2,ty=cy-(y0+y1)*s/2;
  return `<g fill="${c}" transform="translate(${num(tx)} ${num(ty)}) scale(${num(s)})">${g.paths.map(d=>`<path d="${d}"/>`).join('')}</g>`;
}
function wordmark(c,x,y,fontSize=80) {
  const s=fontSize/word.unitsPerEm,[x0,y0,x1,y1]=word.bounds;
  return `<g fill="${c}" transform="translate(${num(x-x0*s)} ${num(y+y1*s)}) scale(${num(s)} ${num(-s)})">${word.paths.map(d=>`<path d="${d}"/>`).join('')}</g>`;
}
async function writeSvg(relative,source,pngRelative,width) {
  fs.writeFileSync(path.join(root,relative),source);
  if(pngRelative)await sharp(Buffer.from(source)).resize({width}).png().toFile(path.join(root,pngRelative));
}
function ico(images) {
  const header=Buffer.alloc(6);header.writeUInt16LE(1,2);header.writeUInt16LE(images.length,4);
  let offset=6+16*images.length;const entries=[];
  for(const {size,buffer}of images){const entry=Buffer.alloc(16);entry[0]=size===256?0:size;entry[1]=entry[0];entry.writeUInt16LE(1,4);entry.writeUInt16LE(32,6);entry.writeUInt32LE(buffer.length,8);entry.writeUInt32LE(offset,12);offset+=buffer.length;entries.push(entry);}
  return Buffer.concat([header,...entries,...images.map(i=>i.buffer)]);
}
async function main() {
  const g=await trace();
  for(const [name,c]of Object.entries(color))await writeSvg(`svg/simbolo-${name}.svg`,svg(256,256,mark(g,c,128,128,200),'Fornada — Forno aberto'),`png/simbolo-${name}-1024.png`,1024);
  for(const [name,markColor,textColor]of [['primary',color.primary,color.ink],['white',color.white,color.white],['ink',color.ink,color.ink]]){
    const horizontal=svg(512,160,mark(g,markColor,80,80,112)+wordmark(textColor,168,49),'Fornada — logo horizontal');
    const vertical=svg(384,360,mark(g,markColor,192,145,220)+wordmark(textColor,57.6,280),'Fornada — logo vertical');
    await writeSvg(`svg/logo-horizontal-${name}.svg`,horizontal,`png/logo-horizontal-${name}-2048.png`,2048);
    await writeSvg(`svg/logo-vertical-${name}.svg`,vertical,`png/logo-vertical-${name}-1536.png`,1536);
  }
  const favicon=svg(256,256,mark(g,color.primary,128,128,240),'Fornada favicon');
  await writeSvg('favicon/favicon.svg',favicon);
  const icoEntries=[];
  for(const size of [16,32,48,64]){const buffer=await sharp(Buffer.from(favicon)).resize(size,size).png().toBuffer();fs.writeFileSync(path.join(root,`favicon/favicon-${size}.png`),buffer);icoEntries.push({size,buffer});}
  fs.writeFileSync(path.join(root,'favicon/favicon.ico'),ico(icoEntries));
  const app=svg(256,256,`<path fill="${color.primary}" d="M0 0H256V256H0Z"/>`+mark(g,color.white,128,128,172),'Fornada — aplicativo');
  await writeSvg('app/app-icon.svg',app);
  for(const size of [192,512,1024])await sharp(Buffer.from(app)).resize(size,size).png().toFile(path.join(root,`app/app-icon-${size}.png`));
  await sharp(Buffer.from(app)).resize(180,180).png().toFile(path.join(root,'app/apple-touch-icon.png'));
  const safe=svg(256,256,`<path fill="${color.primary}" d="M0 0H256V256H0Z"/>`+mark(g,color.white,128,128,128),'Fornada — ícone com área segura de máscara');
  await writeSvg('app/app-maskable.svg',safe,'app/app-maskable-512.png',512);
  const foreground=svg(256,256,mark(g,color.white,128,128,128),'Fornada — foreground Android');
  await writeSvg('app/android-foreground.svg',foreground,'app/android-foreground-432.png',432);
  fs.writeFileSync(path.join(root,'app','manifest-example.webmanifest'),JSON.stringify({name:'Fornada',short_name:'Fornada',lang:'pt-BR',start_url:'/',display:'standalone',background_color:color.cream,theme_color:color.primary,icons:[{src:'./app-icon-192.png',sizes:'192x192',type:'image/png',purpose:'any'},{src:'./app-icon-512.png',sizes:'512x512',type:'image/png',purpose:'any'},{src:'./app-maskable-512.png',sizes:'512x512',type:'image/png',purpose:'maskable'}]},null,2));
  const label=(text,x,y,size=16,fill=color.ink)=>`<text x="${x}" y="${y}" font-family="Segoe UI, sans-serif" font-size="${size}" fill="${fill}">${escape(text)}</text>`;
  const sheet=svg(1440,1040,`<path fill="${color.cream}" d="M0 0H1440V1040H0Z"/>`+label('FORNADA / IDENTIDADE APROVADA · 07 OUT 2026',64,58,13)+label('Forno aberto.',64,138,66)+label('Arco, assadeira e espaço para crescer.',68,178,20)+
    `<path fill="#F4E7DB" d="M64 218H672V650H64Z"/>`+mark(g,color.primary,368,430,290)+label('SÍMBOLO PRINCIPAL',88,622,13)+
    `<path fill="${color.ink}" d="M704 218H1376V444H704Z"/>`+mark(g,color.white,785,330,105)+wordmark(color.white,875,300,82)+label('VERSÃO PARA FUNDO ESCURO',734,414,13,'#DFD0C4')+
    mark(g,color.primary,785,548,105)+wordmark(color.ink,875,518,82)+label('LOGO HORIZONTAL',734,636,13)+
    label('LARANJA FORNO',64,714,13)+`<path fill="${color.primary}" d="M64 734H224V784H64Z"/>`+label(color.primary,64,814,18)+
    label('CACAU',260,714,13)+`<path fill="${color.ink}" d="M260 734H420V784H260Z"/>`+label(color.ink,260,814,18)+
    label('CREME',456,714,13)+`<path fill="${color.cream}" stroke="#D9C9BE" d="M456 734H616V784H456Z"/>`+label(color.cream,456,814,18)+
    label('ÍCONE DO APLICATIVO',734,714,13)+`<rect x="734" y="734" width="140" height="140" rx="31" fill="${color.primary}"/>`+mark(g,color.white,804,804,94)+
    label('FAVICON',950,714,13)+[16,24,32,48].map((s,i)=>mark(g,color.primary,975+i*90,788,s*.9375)+label(`${s}px`,960+i*90,842,13)).join('')+
    label('01 · Símbolo e nome | 02 · Cor e monocromia | 03 · Navegador e celular',64,936,18)+label('Master em SVG · Nome em curvas · Exports PNG / ICO · Área segura para máscaras',64,976,15),'Fornada — prancha de identidade aprovada');
  await writeSvg('prancha.svg',sheet,'prancha.png',1440);
  const allFiles=[];function walk(dir){for(const name of fs.readdirSync(dir)){const p=path.join(dir,name);if(fs.statSync(p).isDirectory())walk(p);else if(/\.(svg|png|ico|webmanifest)$/.test(name))allFiles.push(path.relative(root,p).replaceAll('\\','/'));}}walk(root);
  const validation={version:'1.0',approved:'2026-10-07',source:'Opção 02 e anexo aprovado pelo usuário',geometry:{components:g.components,curves:g.paths.map(p=>(p.match(/C/g)||[]).length),bounds:g.bounds,silhouetteIoU:g.silhouetteIoU},colors:color,wordmark:{font:word.font,text:word.text,outlined:true},files:allFiles};
  fs.writeFileSync(path.join(root,'kit.json'),JSON.stringify(validation,null,2));
  console.log(JSON.stringify({files:allFiles.length,components:g.components,curves:validation.geometry.curves,prancha:path.join(root,'prancha.png')}));
}
main().catch(e=>{console.error(e);process.exit(1);});
