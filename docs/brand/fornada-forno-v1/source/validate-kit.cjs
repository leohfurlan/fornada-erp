const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const sharp=require('C:/Users/Leonardo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root=path.resolve(__dirname,'..');
const kit=JSON.parse(fs.readFileSync(path.join(root,'kit.json'),'utf8'));
async function main(){
  const results=[];
  assert(kit.geometry.silhouetteIoU>.98,'The approved silhouette must remain close to the reference.');
  for(const file of kit.files.filter(f=>f.endsWith('.svg'))){
    const text=fs.readFileSync(path.join(root,file),'utf8');
    assert(!/NaN|Infinity|<image|<script|<foreignObject/i.test(text),file);
    if(file!=='prancha.svg')assert(!/<text[ >]|font-family/i.test(text),`${file}: deliverable must use outlines`);
    results.push({file,check:'Vector without raster, scripts or external font dependency',passed:true});
  }
  for(const file of kit.files.filter(f=>f.endsWith('.png')&&!f.startsWith('source/'))){
    const {data,info}=await sharp(path.join(root,file)).ensureAlpha().raw().toBuffer({resolveWithObject:true});
    let expected,transparent=true;
    if(file.startsWith('png/simbolo'))expected=[1024,1024];
    else if(file.startsWith('png/logo-horizontal'))expected=[2048,640];
    else if(file.startsWith('png/logo-vertical'))expected=[1536,1440];
    else if(file==='app/apple-touch-icon.png'){expected=[180,180];transparent=false;}
    else if(file==='app/android-foreground-432.png')expected=[432,432];
    else if(file==='app/app-maskable-512.png'){expected=[512,512];transparent=false;}
    else if(file.startsWith('app/app-icon-')){const size=Number(file.match(/-(\d+)\.png$/)[1]);expected=[size,size];transparent=false;}
    else if(file.startsWith('favicon/')){const size=Number(file.match(/-(\d+)\.png$/)[1]);expected=[size,size];}
    else if(file==='prancha.png'){expected=[1440,1040];transparent=false;}
    assert.deepEqual([info.width,info.height],expected,file);
    let minAlpha=255,maxAlpha=0;
    for(let i=3;i<data.length;i+=4){minAlpha=Math.min(minAlpha,data[i]);maxAlpha=Math.max(maxAlpha,data[i]);}
    assert.equal(maxAlpha,255,file);
    assert.equal(minAlpha,transparent?0:255,file);
    results.push({file,dimensions:expected,transparent,passed:true});
  }
  const fg=await sharp(path.join(root,'app/android-foreground-432.png')).ensureAlpha().raw().toBuffer({resolveWithObject:true});
  let maxRadius=0;
  for(let y=0;y<432;y++)for(let x=0;x<432;x++)if(fg.data[(y*432+x)*4+3]>=128)maxRadius=Math.max(maxRadius,Math.hypot(x+.5-216,y+.5-216));
  assert(maxRadius<144,'Foreground must fit the central safe circle.');
  results.push({check:'Android foreground within central 2/3 circle',maxRadius,limit:144,passed:true});
  const icon=fs.readFileSync(path.join(root,'favicon/favicon.ico'));
  assert.equal(icon.readUInt16LE(0),0);assert.equal(icon.readUInt16LE(2),1);assert.equal(icon.readUInt16LE(4),4);
  for(let n=0;n<4;n++){const entry=6+n*16,size=[16,32,48,64][n];assert.equal(icon[entry],size);assert.equal(icon[entry+1],size);const offset=icon.readUInt32LE(entry+12),length=icon.readUInt32LE(entry+8);assert(offset+length<=icon.length);assert(icon.subarray(offset,offset+8).equals(Buffer.from([137,80,78,71,13,10,26,10])));}
  results.push({file:'favicon/favicon.ico',sizes:[16,32,48,64],passed:true});
  const manifest=JSON.parse(fs.readFileSync(path.join(root,'app/manifest-example.webmanifest'),'utf8'));
  for(const i of manifest.icons)assert(fs.existsSync(path.join(root,'app',i.src)),i.src);
  results.push({file:'app/manifest-example.webmanifest',check:'All relative icon references exist',passed:true});
  const output={date:'2026-10-07',passed:true,silhouetteIoU:kit.geometry.silhouetteIoU,checks:results};
  fs.writeFileSync(path.join(root,'validacao.json'),JSON.stringify(output,null,2));
  console.log(JSON.stringify({passed:true,checks:results.length,silhouetteIoU:kit.geometry.silhouetteIoU,maxAndroidRadius:maxRadius}));
}
main().catch(e=>{console.error(e);process.exit(1);});
