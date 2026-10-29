const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const M=require('./model.js');
const ASSETS=require('../grassland/tiles32/tileset.json');
ASSETS.biomes={bog:require('../bog/tiles32/tileset.json')};
ASSETS.biomes.burnt_forest=require('../burnt-forest/tiles32/tileset.json');
ASSETS.biomes.wind_plateau=require('../wind_plateau/tiles32/tileset.json');
ASSETS.biomes.wasteland=require('../wasteland/tiles32/tileset.json');

// Run the real editor handlers with a minimal DOM/canvas adapter.
function editor(saved){
  const nodes=new Map(), images=[], tools=[];
  const graphics=new Proxy({}, {get:(target,key)=>target[key]??(()=>{}),set:(target,key,value)=>(target[key]=value,true)});
  function element(){return {
    value:'',children:[],childNodes:[{},{}],dataset:{},style:{},firstChild:{textContent:''},listeners:{},
    classList:{toggle(){},add(){},remove(){}},
    append(...children){this.children.push(...children)},replaceChildren(){this.children=[]},
    setAttribute(){},getContext(){return graphics},getBoundingClientRect(){return {left:0,top:0,width:800,height:600}},
    addEventListener(name,fn){this.listeners[name]=fn},remove(){},close(){},focus(){},setPointerCapture(){},
  }}
  for(const tool of ['brush','rect','fill','erase','pick','pan']){const b=element();b.dataset.tool=tool;tools.push(b)}
  const $=selector=>{if(!nodes.has(selector))nodes.set(selector,element());return nodes.get(selector)};
  const context={MeadowModel:M,ASSETS,devicePixelRatio:1,
    Image:class{constructor(){images.push(this)}},ResizeObserver:class{observe(){}},
    document:{querySelector:$,createElement:element,addEventListener(){},querySelectorAll(selector){
      if(selector==='[data-tool]')return tools;
      if(selector==='.tile')return $('#palette').children.filter(b=>b.className==='tile');
      return [];
    }},window:{addEventListener(){}},localStorage:{getItem:()=>saved?JSON.stringify(saved):null,setItem(){}},
    setTimeout(){},clearTimeout(){},
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(__dirname+'/editor.js','utf8'),context);
  images.forEach(image=>image.onload());
  const run=code=>vm.runInContext(code,context);
  const tileCount=()=>$('#palette').children.filter(b=>b.className==='tile').length;
  function create(biome){$('#newBiome').value=biome;$('#newWidth').value='8';$('#newHeight').value='8';$('#newName').value=biome;$('#newForm').onsubmit({preventDefault(){}})}
  return {$,run,tileCount,create,tools};
}

const e=editor();
assert.equal(e.tileCount(),64);
for(const biome of M.biomes.filter(b=>!['grassland','bog','burnt_forest','wind_plateau','wasteland'].includes(b.id))){
  e.create(biome.id);
  assert.equal(e.tileCount(),0);
  assert.equal(e.$('#tileCount').textContent,0);
  assert.equal(e.$('#filters').children.length,0);
  assert.equal(e.run('selected'),null);
  assert.equal(e.run('randomMapButton.disabled'),true);
  assert.equal(e.$('#search').disabled,true);
  assert.ok(e.tools.every(b=>b.dataset.tool==='pan'?!b.disabled:b.disabled));
  const before=e.run('JSON.stringify(map)');
  e.run("randomMapButton.onclick();setTool('fill');setCell(0,0,3);choose(3)");
  assert.equal(e.run('JSON.stringify(map)'),before);
  assert.equal(e.run('selected'),null);
  assert.equal(e.run('tool'),'pan');
  e.run('travel()');
  assert.equal(e.tileCount(),64);
  assert.equal(e.run('randomMapButton.disabled'),false);
  e.run('travel(true)');
  assert.equal(e.tileCount(),0);
  e.create('grassland');
  assert.equal(e.tileCount(),64);
  assert.ok(e.tools.every(b=>!b.disabled));
}
const restored=editor(M.create(8,8,'saved','snowfield'));
assert.equal(restored.tileCount(),0);
assert.equal(restored.run('selected'),null);
e.create('bog');
assert.equal(e.tileCount(),16);
assert.equal(e.run('selected'),0);
assert.equal(e.run('randomMapButton.disabled'),false);
assert.ok(e.tools.every(b=>!b.disabled));
assert.equal(e.run('activeAssets().tiles[0].name'),ASSETS.biomes.bog.tiles[0].name);
assert.equal(e.run('map.tileset'),'../bog/tiles32/bog-32.webp');
e.run("setTool('brush');setCell(0,0,0)");
assert.equal(e.run('map.data[0]'),0);
e.run('travel()');assert.equal(e.tileCount(),64);
e.run('travel(true)');assert.equal(e.tileCount(),16);
const restoredBog=editor(M.create(8,8,'bog','bog'));
assert.equal(restoredBog.tileCount(),16);assert.equal(restoredBog.run('selected'),0);
restoredBog.run('choose(15);setCell(0,0,15)');
assert.equal(restoredBog.run('map.data[0]'),15);
assert.equal(restoredBog.run('M.validate(JSON.parse(JSON.stringify(map))).data[0]'),15);
restoredBog.run('randomMapButton.onclick()');
assert.ok(restoredBog.run('map.data.every(id=>id>=0&&id<16)'));
assert.equal(restoredBog.run('history.past.length'),1);
restoredBog.run('travel()');assert.equal(restoredBog.run('map.data[0]'),15);
console.log('Passed: biome palette counts, empty selection, tool/random guards, biome transitions, undo/redo, saved biome restoration.');
e.create('burnt_forest');
assert.equal(e.tileCount(),19);assert.equal(e.run('selected'),0);
assert.equal(e.run('randomMapButton.disabled'),false);
assert.ok(e.tools.every(b=>!b.disabled));
assert.equal(e.run('map.tileset'),'../burnt-forest/tiles32/burnt-forest-32.webp');
assert.equal(e.run('activeAssets().tiles[0].name'),ASSETS.biomes.burnt_forest.tiles[0].name);
e.run('travel()');assert.equal(e.tileCount(),16);
e.run('travel(true)');assert.equal(e.tileCount(),19);
const restoredVolcano=editor(M.create(8,8,'burnt_forest','burnt_forest'));
assert.equal(restoredVolcano.tileCount(),19);
assert.equal(restoredVolcano.run('M.validate(JSON.parse(JSON.stringify(map))).biome'),'burnt_forest');
restoredVolcano.run('choose(21);setCell(0,0,21)');
assert.equal(restoredVolcano.run('M.validate(JSON.parse(JSON.stringify(map))).data[0]'),21);
restoredVolcano.run('randomMapButton.onclick()');
assert.ok(restoredVolcano.run('map.data.every(id=>id>=0&&id<43)'));
restoredVolcano.run('travel()');assert.equal(restoredVolcano.run('map.data[0]'),21);
assert.equal(restoredVolcano.run("availableTiles().filter(t=>t.category==='embers').length"),9);
assert.ok(restoredVolcano.run('availableTiles().every(t=>![10,11,12].includes(t.id))'));
restoredVolcano.run('randomMapButton.onclick()');
assert.ok(restoredVolcano.run('map.data.every(id=>![10,11,12].includes(id))'));
e.create('wind_plateau');
assert.equal(e.tileCount(),16);assert.equal(e.run('selected'),0);
assert.equal(e.run('randomMapButton.disabled'),false);
assert.equal(e.run('map.tileset'),'../wind_plateau/tiles32/wind_plateau-32.webp');
e.run('choose(15);setCell(0,0,15)');
assert.equal(e.run('M.validate(JSON.parse(JSON.stringify(map))).data[0]'),15);
e.run('randomMapButton.onclick()');
assert.ok(e.run('map.data.every(id=>id>=0&&id<16)'));
e.run('travel()');assert.equal(e.run('map.data[0]'),15);
const restoredPlateau=editor(M.create(8,8,'plateau','wind_plateau'));
assert.equal(restoredPlateau.tileCount(),16);
e.create('wasteland');
assert.equal(e.tileCount(),25);assert.equal(e.run('selected'),0);
assert.ok(!ASSETS.biomes.wasteland.tiles.filter(t=>!t.hidden).some(t=>[1,2,3,4,5].includes(t.family)));
assert.equal(e.run('randomMapButton.disabled'),false);
assert.equal(e.run('map.tileset'),'../wasteland/tiles32/wasteland-32.webp');
e.run('choose(15);setCell(0,0,15)');
assert.equal(e.run('M.validate(JSON.parse(JSON.stringify(map))).data[0]'),15);
e.run('randomMapButton.onclick()');
assert.ok(e.run('map.data.every(id=>id>=0&&id<43)'));
e.run('travel()');assert.equal(e.run('map.data[0]'),15);
assert.equal(editor(M.create(8,8,'wasteland','wasteland')).tileCount(),25);

