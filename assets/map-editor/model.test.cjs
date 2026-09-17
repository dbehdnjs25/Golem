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
for(const bad of [{...map,width:0},{...map,version:2},{...map,data:[1]},{...map,tileSize:64},{...map,data:map.data.map(()=>16)},{...map,width:4.5},null])assert.throws(()=>M.validate(bad));
const large=M.create(128,128);M.fill(large,0,0,15);assert.ok(large.data.every(n=>n===15));
console.log('Passed: bounded fill, continuous stroke, resize preservation, undo/redo branching, JSON roundtrip, invalid import rejection, maximum-size fill.');
