const assert=require('node:assert/strict');
const M=require('./model.js');
let map=M.create(8,8,'테스트');
for(let y=0;y<8;y++)M.put(map,4,y,8);
M.fill(map,0,0,3);
assert.equal(map.data[0],3);assert.equal(map.data[7],0);assert.equal(map.data[4],8);
M.fill(map,0,0,3); // no-op fill must terminate
const points=[];M.line(0,0,7,3,(x,y)=>points.push([x,y]));assert.deepEqual(points[0],[0,0]);assert.deepEqual(points.at(-1),[7,3]);assert.equal(points.length,8);
const enlarged=M.resize(map,12,10);assert.equal(enlarged.data[4],8);assert.equal(enlarged.data[9*12+11],0);assert.equal(enlarged.data[7*12+4],8);
const h=new M.History(),before=M.clone(map);M.put(map,1,1,14);h.commit(before,map);map=h.undo(map);assert.equal(map.data[9],3);map=h.redo(map);assert.equal(map.data[9],14);map=h.undo(map);const branch=M.clone(map);M.put(map,0,0,5);h.commit(branch,map);assert.equal(h.future.length,0);
assert.deepEqual(M.validate(JSON.parse(JSON.stringify(map))),map);
for(const bad of [{...map,width:0},{...map,version:2},{...map,data:[1]},{...map,tileSize:64},{...map,data:map.data.map(()=>64)},{...map,width:4.5},null])assert.throws(()=>M.validate(bad));
const large=M.create(128,128);M.fill(large,0,0,15);assert.ok(large.data.every(n=>n===15));
console.log('Passed: bounded fill, continuous stroke, resize preservation, undo/redo branching, JSON roundtrip, invalid import rejection, maximum-size fill.');

const variants=M.create(8,8,'랜덤 배치와 클로버');
for(let id=0;id<64;id++) variants.data[id]=id;
assert.deepEqual(M.validate(JSON.parse(JSON.stringify(variants))),variants);
assert.throws(()=>M.validate({...variants,data:variants.data.map(()=>-1)}));
assert.throws(()=>M.validate(variants,16));
assert.equal(M.resize(variants,12,12).data[5*12+7],47);
assert.equal(M.resize(variants,12,12).data[6*12+3],51);
assert.equal(M.resize(variants,12,12).data[7*12+7],63);
const assets=require('../grassland/tiles32/tileset.json');
let seed=20260919;const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296};
const original=M.clone(variants), scattered=M.randomize(variants,assets.tiles,random);
assert.deepEqual(variants,original);
assert.equal(scattered.width,variants.width);assert.equal(scattered.name,variants.name);
assert.deepEqual(M.validate(JSON.parse(JSON.stringify(scattered))),scattered);
assert.ok(new Set(scattered.data).size>5);assert.ok(scattered.data.includes(0));
assert.ok(M.randomize(variants,assets.tiles,()=>.74).data.every(id=>id===0));
assert.ok(M.randomize(variants,assets.tiles,()=>.76).data.every(id=>id!==0));
const randomHistory=new M.History();randomHistory.commit(original,scattered);
assert.deepEqual(randomHistory.undo(scattered),original);
assert.deepEqual(randomHistory.redo(original),scattered);
assert.ok(M.randomize(variants,[],random).data.every(id=>id===0));
assert.ok(M.randomize(variants,assets.tiles,()=>.999).data.every(id=>id===47));
console.log('Passed: whole-map random placement, valid IDs, unchanged dimensions, JSON roundtrip, single-step undo/redo.');
assert.deepEqual(M.biomes.map(b=>b.id),['grassland','bog','burnt_forest','wind_plateau','wasteland','snowfield']);
const legacy=M.clone(map);delete legacy.biome;
const oldPlateau={...M.create(8,8,'old plateau','wind_plateau'),tileset:'../grassland/tiles32/grassland-32.webp',data:Array(64).fill(3)};
const oldWasteland={...M.create(8,8,'old wasteland','wasteland'),tileset:'../grassland/tiles32/grassland-32.webp',data:Array(64).fill(3)};
assert.ok(M.validate(oldWasteland).data.every(id=>id===0));
assert.throws(()=>M.validate({...M.create(8,8,'wasteland','wasteland'),data:Array(64).fill(43)}));
assert.ok(M.validate(oldPlateau).data.every(id=>id===0));
assert.throws(()=>M.validate({...M.create(8,8,'plateau','wind_plateau'),data:Array(64).fill(16)}));
assert.equal(M.validate(legacy).biome,'grassland');
for(const {id,name} of M.biomes){
  const lastTile=['bog','wind_plateau'].includes(id)?15:id==='wasteland'?42:id==='burnt_forest'?21:63;
  const biomeMap=M.create(8,8,name,id);M.put(biomeMap,7,7,lastTile);
  assert.equal(biomeMap.biome,id);
  assert.deepEqual(M.validate(JSON.parse(JSON.stringify(biomeMap))),biomeMap);
  const resized=M.resize(biomeMap,12,12);
  assert.equal(resized.biome,id);assert.equal(resized.data[7*12+7],lastTile);
  assert.equal(M.randomize(biomeMap,assets.tiles,random).biome,id);
  const history=new M.History();history.commit(map,biomeMap);
  assert.deepEqual(history.undo(biomeMap),map);
  assert.deepEqual(history.redo(map),biomeMap);
}
for(const biome of ['unknown','',null,0,{}]){
  assert.throws(()=>M.create(8,8,'invalid',biome));
  assert.throws(()=>M.validate({...map,biome}));
}
console.log('Passed: six biomes, legacy migration, JSON persistence, resize/randomize preservation, undo/redo, invalid biome rejection.');
const oldBog={...M.create(8,8,'old bog','bog'),tileset:'../grassland/tiles32/grassland-32.webp',data:Array(64).fill(3)};
assert.ok(M.validate(oldBog).data.every(id=>id===0));
assert.throws(()=>M.validate({...M.create(8,8,'bog','bog'),data:Array(64).fill(16)}));
const oldVolcano={...M.create(8,8,'old volcano','burnt_forest'),tileset:'../grassland/tiles32/grassland-32.webp',data:Array(64).fill(3)};
assert.ok(M.validate(oldVolcano).data.every(id=>id===0));
assert.throws(()=>M.validate({...M.create(8,8,'burnt_forest','burnt_forest'),data:Array(64).fill(43)}));
for(const retired of [10,11,12]){
  const saved=M.create(8,8,'embers','burnt_forest');saved.data[0]=retired;
  assert.equal(M.validate(saved).data[0],retired+6);
}
