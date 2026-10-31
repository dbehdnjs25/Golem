const $ = s => document.querySelector(s), M=MeadowModel;
const image=new Image(), history=new M.History(), surface=document.createElement('canvas'), sc=surface.getContext('2d');
const atlasImages={grassland:image,...Object.fromEntries(Object.keys(ASSETS.biomes).map(id=>[id,new Image()]))};let loadedAtlases=0;
const canvas=$('#canvas'), ctx=canvas.getContext('2d'), viewport=$('#viewport');
const storageKey='meadow-studio-map-v1';
const activeAssets=()=>ASSETS.biomes[map.biome]||ASSETS;
const availableTiles=()=>atlasImages[map.biome]?activeAssets().tiles.filter(tile=>!tile.hidden):[];
let libraryBiome=null;
let map=M.create(), selected=3, tool='brush', brush=1, category='all', hover=null;
let scale=1, ox=0, oy=0, vw=0, vh=0, ready=false, gesture=null, space=false, toastTimer, storageOkay=true;
try{const saved=localStorage.getItem(storageKey);if(saved)map=M.validate(JSON.parse(saved),ASSETS.tilecount)}catch{storageOkay=false}
const hints={brush:'드래그해서 그리기 · 우클릭으로 타일 추출',rect:'드래그한 사각 영역을 선택한 타일로 채우기',fill:'같은 타일로 연결된 영역을 한 번에 채우기',erase:'장식을 지우고 바이옴의 기본 땅으로 되돌리기',pick:'캔버스의 타일을 골라 브러시로 사용하기',pan:'드래그해서 화면 이동 · 마우스 휠로 확대·축소'};
function toast(message){$('#toast').textContent=message;$('#toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),2800)}
function saveLocal(){try{localStorage.setItem(storageKey,JSON.stringify(map));storageOkay=true;$('#saveState').textContent='● 브라우저에 자동 저장됨'}catch{storageOkay=false;$('#saveState').textContent='자동 저장 불가 · JSON으로 저장하세요'}}
function tile(c,id,x,y,size=32){const assets=activeAssets();c.imageSmoothingEnabled=false;c.drawImage(atlasImages[map.biome]||image,...(assets.tiles[id]||assets.tiles[0]).rect,x,y,size,size)}
function sync(){
  $('#mapName').value=map.name;$('#canvasName').textContent=`${map.name} · ${M.biomes.find(b=>b.id===map.biome).name}`;$('#dimensions').textContent=`${map.width} × ${map.height} 타일`;
  $('#mapPixels').textContent=`${map.width*32} × ${map.height*32} px`;$('#mapWidth').value=map.width;$('#mapHeight').value=map.height;
  $('#undo').disabled=!history.past.length;$('#redo').disabled=!history.future.length;
}
function rebuild(){surface.width=map.width*32;surface.height=map.height*32;sc.imageSmoothingEnabled=false;for(let y=0;y<map.height;y++)for(let x=0;x<map.width;x++)tile(sc,map.data[y*map.width+x],x*32,y*32);if(libraryBiome!==map.biome){libraryBiome=map.biome;selected=0;category='all';$('#search').value='';filters();palette();setTool(availableTiles().length?'brush':'pan')}sync();draw()}
function setCell(x,y,id){if(!availableTiles().length||id===null||x<0||y<0||x>=map.width||y>=map.height)return;if(map.data[y*map.width+x]===id)return;M.put(map,x,y,id);tile(sc,id,x*32,y*32)}
function mini(){if(!$('#showMini').checked)return;const c=$('#minimap');const ratio=map.width/map.height;c.width=Math.max(1,Math.round(Math.min(192,144*ratio)));c.height=Math.max(1,Math.round(c.width/ratio));c.style.width=c.width+'px';const m=c.getContext('2d');m.imageSmoothingEnabled=false;m.drawImage(surface,0,0,c.width,c.height);const factor=c.width/surface.width;m.strokeStyle='#fcffe7';m.lineWidth=2;m.strokeRect(-ox/scale*factor,-oy/scale*factor,vw/scale*factor,vh/scale*factor)}
function draw(){if(!ready)return;const dpr=devicePixelRatio||1;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,vw,vh);ctx.imageSmoothingEnabled=false;
  ctx.save();ctx.shadowColor='#283e2720';ctx.shadowBlur=22;ctx.shadowOffsetY=7;ctx.fillStyle='#75994f';ctx.fillRect(ox,oy,surface.width*scale,surface.height*scale);ctx.restore();
  ctx.drawImage(surface,ox,oy,surface.width*scale,surface.height*scale);
  const step=32*scale;if($('#showGrid').checked&&step>=8){ctx.save();ctx.beginPath();ctx.rect(ox,oy,surface.width*scale,surface.height*scale);ctx.clip();ctx.strokeStyle='#27462835';ctx.lineWidth=1;ctx.beginPath();for(let x=0;x<=map.width;x++){const px=ox+x*step;ctx.moveTo(px,oy);ctx.lineTo(px,oy+surface.height*scale)}for(let y=0;y<=map.height;y++){const py=oy+y*step;ctx.moveTo(ox,py);ctx.lineTo(ox+surface.width*scale,py)}ctx.stroke();ctx.restore()}
  let box=null;
  if(gesture?.kind==='rect'){const a=gesture.start,b=gesture.last;box=[Math.min(a.x,b.x),Math.min(a.y,b.y),Math.abs(a.x-b.x)+1,Math.abs(a.y-b.y)+1]}
  else if(hover&&inside(hover)&&['brush','erase','rect','fill','pick'].includes(tool)&&!space){const n=['brush','erase'].includes(tool)?brush:1;box=[hover.x-Math.floor(n/2),hover.y-Math.floor(n/2),n,n]}
  if(box){ctx.save();ctx.beginPath();ctx.rect(ox,oy,surface.width*scale,surface.height*scale);ctx.clip();ctx.fillStyle=tool==='erase'?'#f2c89040':'#ffffff35';ctx.strokeStyle='#fbffe9';ctx.lineWidth=1.5;ctx.fillRect(ox+box[0]*step,oy+box[1]*step,box[2]*step,box[3]*step);ctx.strokeRect(ox+box[0]*step+.5,oy+box[1]*step+.5,box[2]*step-1,box[3]*step-1);ctx.restore()}
  $('#zoomLabel').textContent=Math.round(scale*100)+'%';mini();
}
function fit(){const pad=90;scale=Math.max(.08,Math.min(3,(vw-pad)/surface.width,(vh-pad)/surface.height));ox=(vw-surface.width*scale)/2;oy=(vh-surface.height*scale)/2;draw()}
function zoom(factor,x=vw/2,y=vh/2){const next=Math.min(6,Math.max(.08,scale*factor));ox=x-(x-ox)*next/scale;oy=y-(y-oy)*next/scale;scale=next;draw()}
function point(e){const r=canvas.getBoundingClientRect();return {x:Math.floor((e.clientX-r.left-ox)/(32*scale)),y:Math.floor((e.clientY-r.top-oy)/(32*scale))}}
const inside=p=>p.x>=0&&p.y>=0&&p.x<map.width&&p.y<map.height;
function choose(id){const tiles=availableTiles();if(!tiles.length){selected=null;$('#selectedTile').getContext('2d').clearRect(0,0,32,32);$('#selectedName').textContent='선택 가능한 타일 없음';$('#selectedId').textContent='바이옴 타일 준비 중';draw();return}if(!tiles.some(t=>t.id===id))id=tiles[0].id;selected=id;tile($('#selectedTile').getContext('2d'),id,0,0);$('#selectedName').textContent=activeAssets().tiles[id].name;$('#selectedId').textContent=`${map.biome==='grassland'?'GRASS':map.biome==='burnt_forest'?'BURNT':map.biome.toUpperCase()}_${String(id).padStart(2,'0')} · 32 × 32`;document.querySelectorAll('.tile').forEach(b=>{b.classList.toggle('active',Number(b.dataset.id)===id);b.setAttribute('aria-pressed',String(Number(b.dataset.id)===id))});draw()}
function setTool(value){finish();const empty=!availableTiles().length;tool=empty?'pan':value;document.querySelectorAll('[data-tool]').forEach(b=>{b.disabled=empty&&b.dataset.tool!=='pan';b.classList.toggle('active',b.dataset.tool===tool);b.setAttribute('aria-pressed',String(b.dataset.tool===tool))});$('#toolHint').textContent=empty?'바이옴 타일 준비 중 · 화면 이동과 확대·축소 가능':hints[tool];canvas.style.cursor=tool==='pan'?'grab':tool==='pick'?'copy':'crosshair';$('#brushSize').disabled=empty||!['brush','erase'].includes(tool);draw()}
const categories=[['all','전체'],['ground','기본 땅'],['water','물결'],['embers','불씨'],['wood','탄 나무'],['charcoal','숯 조각'],['plants','잔디·풀'],['debris','부유물'],['flowers','한 송이 꽃'],['clusters','꽃 무리'],['stones','돌'],['mixed','혼합'],['random','전체 랜덤']];
function filters(){
  const tiles=availableTiles(),empty=!tiles.length;
  $('#tileCount').textContent=tiles.length;
  $('.library .panel-heading h2').firstChild.textContent=`${M.biomes.find(b=>b.id===map.biome).name}의 재료 `;
  $('.library-foot').hidden=empty;
  if(!empty)$('.library-foot').childNodes[1].textContent=` ${M.biomes.find(b=>b.id===map.biome).name} 타일 세트 `;
  $('#search').disabled=empty;
  randomMapButton.disabled=!ready||tiles.length<2;
  randomMapHint.textContent=empty?'이 바이옴의 타일은 아직 준비 중입니다.':tiles.length===1?'기본 땅 1종 · 랜덤 배치는 변형 추가 후 사용 가능합니다.':map.biome==='bog'?'맵 전체에 물결·수생 식물·부유물을 섞어 배치':map.biome==='burnt_forest'?'맵 전체에 탄 나무·숯 조각·불씨를 섞어 배치':map.biome==='wind_plateau'?'맵 전체에 고원 풀·자갈·풍화된 바위를 섞어 배치':map.biome==='snowfield'?'\uAE30\uBCF8 \uB208 \uB545 90% \u00B7 \uB208\uB355\uC774\uC640 \uC5BC\uC74C \uD0C0\uC77C\uC744 \uC11E\uC5B4 \uBC30\uCE58':map.biome==='wasteland'?'기본 땅 약 75% · 갈라진 땅 변형을 섞어 배치':'맵 전체에 꽃·풀·돌을 섞어 배치 · 실행 취소 가능';
  $('#filters').replaceChildren();
  if(empty)return;
  for(const [id,label] of categories){
    const b=document.createElement('button');b.dataset.category=id;
    const count=tiles.filter(a=>id==='all'||a.category===id).length;
    if(!count)continue;
    b.textContent=`${map.biome==='bog'&&id==='plants'?'수생 식물':label} ${count}`;b.classList.toggle('active',category===id);
    b.setAttribute('aria-pressed',String(category===id));$('#filters').append(b);
  }
}
function palette(){
  const q=$('#search').value.trim();$('#palette').replaceChildren();
  const tiles=availableTiles();
  const visible=tiles.filter(a=>(category==='all'||a.category===category)&&a.name.includes(q));
  const groups=new Map();
  for(const a of visible){if(!groups.has(a.family))groups.set(a.family,[]);groups.get(a.family).push(a)}
  for(const [family,variants] of groups){
    const heading=document.createElement('div');heading.className='palette-heading';
    heading.textContent=activeAssets().tiles[family].name.split(' · ')[0];$('#palette').append(heading);
    for(const a of variants){
      const b=document.createElement('button');b.className='tile';b.dataset.id=a.id;b.title=a.name;b.setAttribute('aria-label',a.name);
      const c=document.createElement('canvas');c.width=c.height=32;tile(c.getContext('2d'),a.id,0,0);
      const label=document.createElement('span');label.textContent=a.position;
      b.append(c,label);b.onclick=()=>{choose(a.id);if(['pick','erase','pan'].includes(tool))setTool('brush')};$('#palette').append(b);
    }
  }
  $('#paletteCount').textContent=!tiles.length?'이 바이옴에는 아직 등록된 타일이 없습니다.':visible.length?`${visible.length}개 타일 · 위치를 골라 사용하세요`:'검색 결과가 없습니다.';
  choose(selected);
}
function stamp(p,id){const half=Math.floor(brush/2);for(let y=p.y-half;y<=p.y+half;y++)for(let x=p.x-half;x<=p.x+half;x++)setCell(x,y,id)}
function commit(before){if(history.commit(before,map)){saveLocal();sync()}draw()}
const randomMapButton=document.createElement('button');
randomMapButton.id='randomizeMap';randomMapButton.className='primary full';
randomMapButton.textContent='전체 랜덤 배치';randomMapButton.disabled=true;
randomMapButton.onclick=()=>{if(!ready||availableTiles().length<2)return;finish();const before=M.clone(map);map=M.randomize(map,availableTiles());rebuild();commit(before);toast('맵 전체를 랜덤 배치했습니다. Ctrl+Z로 되돌릴 수 있어요.')};
const randomMapHint=document.createElement('p');randomMapHint.className='random-map-hint';
randomMapHint.textContent='맵 전체에 꽃·풀·돌을 섞어 배치 · 실행 취소 가능';
$('.library .panel-heading').append(randomMapButton,randomMapHint);
function finish(cancel=false){if(!gesture)return;const g=gesture;gesture=null;if(g.kind==='pan')return;if(cancel){map=g.before;rebuild();return}if(g.kind==='rect'){const a=g.start,b=g.last;for(let y=Math.max(0,Math.min(a.y,b.y));y<=Math.min(map.height-1,Math.max(a.y,b.y));y++)for(let x=Math.max(0,Math.min(a.x,b.x));x<=Math.min(map.width-1,Math.max(a.x,b.x));x++)setCell(x,y,g.id)}commit(g.before)}
canvas.addEventListener('contextmenu',e=>e.preventDefault());
canvas.addEventListener('pointerdown',e=>{
  if(!ready||gesture)return;canvas.focus({preventScroll:true});const p=point(e);hover=p;
  if(e.button===2){if(availableTiles().length&&inside(p)){choose(map.data[p.y*map.width+p.x]);setTool('brush')}return}
  if(e.button!==0&&e.button!==1)return;e.preventDefault();canvas.setPointerCapture(e.pointerId);
  if(space||tool==='pan'||e.button===1){gesture={kind:'pan',px:e.clientX,py:e.clientY,ox,oy};return}
  if(!availableTiles().length||!inside(p))return;
  if(tool==='pick'){choose(map.data[p.y*map.width+p.x]);setTool('brush');return}
  const before=M.clone(map);if(tool==='fill'){M.fill(map,p.x,p.y,selected);rebuild();commit(before);return}
  gesture={kind:tool,before,start:p,last:p,id:tool==='erase'?0:selected};if(tool!=='rect')stamp(p,gesture.id);draw();
});
canvas.addEventListener('pointermove',e=>{if(!ready)return;hover=point(e);$('#position').textContent=inside(hover)?`${hover.x}, ${hover.y}`:'—, —';if(gesture){if(gesture.kind==='pan'){ox=gesture.ox+e.clientX-gesture.px;oy=gesture.oy+e.clientY-gesture.py}else{const p={x:Math.max(0,Math.min(map.width-1,hover.x)),y:Math.max(0,Math.min(map.height-1,hover.y))};if(gesture.kind!=='rect')M.line(gesture.last.x,gesture.last.y,p.x,p.y,(x,y)=>stamp({x,y},gesture.id));gesture.last=p}}draw()});
canvas.addEventListener('pointerup',()=>finish());canvas.addEventListener('pointercancel',()=>finish(true));canvas.addEventListener('lostpointercapture',()=>finish());canvas.addEventListener('pointerleave',()=>{hover=null;draw()});
canvas.addEventListener('wheel',e=>{e.preventDefault();if(gesture||e.deltaY===0)return;const r=canvas.getBoundingClientRect();zoom(e.deltaY<0?1.016:1/1.016,e.clientX-r.left,e.clientY-r.top)},{passive:false});
$('#tools').onclick=e=>{const b=e.target.closest('[data-tool]');if(b)setTool(b.dataset.tool)};
$('#filters').onclick=e=>{const b=e.target.closest('[data-category]');if(!b)return;category=b.dataset.category;filters();palette()};
$('#search').oninput=palette;$('#brushSize').oninput=e=>{brush=Number(e.target.value);$('#brushValue').textContent=`${brush} × ${brush}`;draw()};
$('#showGrid').onchange=draw;$('#showMini').onchange=()=>{$('#miniSection').hidden=!$('#showMini').checked;draw()};
$('#zoomIn').onclick=()=>zoom(1.25);$('#zoomOut').onclick=()=>zoom(.8);$('#fit').onclick=fit;
$('#minimap').onclick=e=>{const r=e.target.getBoundingClientRect();ox=vw/2-(e.clientX-r.left)/r.width*surface.width*scale;oy=vh/2-(e.clientY-r.top)/r.height*surface.height*scale;draw()};
function travel(redo=false){finish();const available=redo?history.future.length:history.past.length;if(!available)return;map=redo?history.redo(map):history.undo(map);rebuild();saveLocal();toast(redo?'다시 실행했습니다.':'이전 작업으로 돌아갔습니다.')}
$('#undo').onclick=()=>travel();$('#redo').onclick=()=>travel(true);
$('#mapName').onchange=()=>{const before=M.clone(map);map.name=$('#mapName').value.trim()||'이름 없는 초원';commit(before);sync()};
$('#resize').onclick=()=>{finish();try{const before=M.clone(map);map=M.resize(map,Number($('#mapWidth').value),Number($('#mapHeight').value));rebuild();commit(before);fit();toast('맵 크기를 변경했습니다.')}catch(e){toast(e.message)}};
function filename(){return (map.name.replace(/[<>:"/\\|?*\x00-\x1f]/g,'_').trim()||'meadow').slice(0,80)}
function download(blob,name){const a=document.createElement('a');const url=URL.createObjectURL(blob);a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),15000)}
function save(){finish();download(new Blob([JSON.stringify(map,null,2)],{type:'application/json'}),filename()+'.json');saveLocal();toast('맵 JSON을 다운로드했습니다.')}
$('#save').onclick=save;$('#load').onclick=()=>$('#file').click();
$('#file').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>2e6)throw Error('2MB 이하의 맵 JSON을 선택하세요.');const next=M.validate(JSON.parse(await file.text()),ASSETS.tilecount);finish();const before=M.clone(map);map=next;rebuild();commit(before);fit();toast('맵을 불러왔습니다. 실행 취소로 이전 맵에 돌아갈 수 있어요.')}catch(error){toast(error instanceof SyntaxError?'JSON 파일을 읽을 수 없습니다.':error.message)}finally{e.target.value=''}};
$('#exportImage').onclick=()=>{finish();const name=filename();surface.toBlob(blob=>{if(!blob||blob.type!=='image/webp'){toast('이 브라우저는 WebP 저장을 지원하지 않습니다. Chrome을 사용하세요.');return}download(blob,name+'.webp');toast('격자 없는 맵 이미지를 저장했습니다.')},'image/webp',1)};
$('#newMap').onclick=()=>$('#newDialog').showModal();$('#help').onclick=()=>$('#helpDialog').showModal();
document.querySelectorAll('.close-dialog').forEach(b=>b.onclick=()=>b.closest('dialog').close());
for(const biome of M.biomes){const option=document.createElement('option');option.value=biome.id;option.textContent=biome.name;$('#newBiome').append(option)}
$('#newBiome').onchange=()=>{const name=$('#newName');if(!name.value.trim()||M.biomes.some(b=>name.value===`새로운 ${b.name}`))name.value=`새로운 ${M.biomes.find(b=>b.id===$('#newBiome').value).name}`};
$('#newForm').onsubmit=e=>{e.preventDefault();try{const biome=$('#newBiome').value;const next=M.create(Number($('#newWidth').value),Number($('#newHeight').value),$('#newName').value.trim()||`새로운 ${M.biomes.find(b=>b.id===biome).name}`,biome);finish();const before=M.clone(map);map=next;rebuild();commit(before);fit();$('#newDialog').close();toast(`${M.biomes.find(b=>b.id===biome).name} 맵을 만들었습니다.`)}catch(error){toast(error.message)}};
document.addEventListener('keydown',e=>{if(e.target.matches('input,textarea,select')||document.querySelector('dialog[open]'))return;const key=e.key.toLowerCase(),mod=e.ctrlKey||e.metaKey;if(mod&&['z','y','s'].includes(key)){e.preventDefault();if(key==='s')save();else travel(key==='y'||e.shiftKey);return}if(e.code==='Space'){e.preventDefault();space=true;canvas.style.cursor='grab';return}if(e.key==='Escape'){finish(true);return}if(mod||e.altKey)return;const keys={b:'brush',r:'rect',f:'fill',e:'erase',i:'pick',h:'pan'};if(keys[key]){e.preventDefault();setTool(keys[key])}if(key==='g'){$('#showGrid').checked=!$('#showGrid').checked;draw()}});
document.addEventListener('keyup',e=>{if(e.code==='Space'){space=false;canvas.style.cursor=tool==='pan'?'grab':'crosshair'}});
window.addEventListener('blur',()=>{space=false;finish()});window.addEventListener('pagehide',()=>{finish();if(ready)saveLocal()});
new ResizeObserver(()=>{const r=viewport.getBoundingClientRect();const oldW=vw,oldH=vh;vw=r.width;vh=r.height;canvas.width=Math.round(vw*(devicePixelRatio||1));canvas.height=Math.round(vh*(devicePixelRatio||1));if(ready){if(oldW){ox+=(vw-oldW)/2;oy+=(vh-oldH)/2;draw()}else fit()}}).observe(viewport);
for(const [biome,atlas] of Object.entries(atlasImages)){
  atlas.onload=()=>{if(++loadedAtlases<Object.keys(atlasImages).length)return;ready=true;$('#loading').remove();rebuild();fit();if(storageOkay)saveLocal();else $('#saveState').textContent='자동 복원 불가 · JSON으로 저장하세요'};
  atlas.onerror=()=>{$('#loading').textContent='타일을 열지 못했습니다. HTML 파일을 다시 생성해 주세요.'};
  atlas.src=(biome==='grassland'?ASSETS:ASSETS.biomes[biome]).url;
}
