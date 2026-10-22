/* Pure map operations, shared by the editor and Node tests. */
const MeadowModel = (() => {
  const biomes = Object.freeze([
    {id:'grassland',name:'초원'}, {id:'bog',name:'늪지'},
    {id:'burnt_forest',name:'불탄 숲'}, {id:'wind_plateau',name:'바람 고원'},
    {id:'wasteland',name:'황무지'}, {id:'snowfield',name:'설원'},
  ].map(Object.freeze));
  const size = n => Number.isInteger(n) && n >= 4 && n <= 128;
  function create(width = 32, height = 24, name = '나의 첫 초원', biome = 'grassland') {
    if(biome==='volcano')biome='burnt_forest';
    if (!size(width) || !size(height)) throw Error('맵 크기는 4~128칸이어야 합니다.');
    if (!biomes.some(b=>b.id===biome)) throw Error('올바른 바이옴을 선택하세요.');
    return {format:'meadow-map', version:1, name, biome, width, height, tileSize:32,
      tileset:biome==='burnt_forest'?'../burnt-forest/tiles32/burnt-forest-32.webp':['bog','wind_plateau','wasteland'].includes(biome)?`../${biome}/tiles32/${biome}-32.webp`:'../grassland/tiles32/grassland-32.webp', data:Array(width*height).fill(0)};
  }
  function validate(raw, tileCount = 64) {
    if (!raw || raw.format !== 'meadow-map' || raw.version !== 1 || raw.tileSize !== 32 ||
        !size(raw.width) || !size(raw.height) || !Array.isArray(raw.data) ||
        raw.data.length !== raw.width*raw.height ||
        !raw.data.every(n => Number.isInteger(n) && n >= 0 && n < tileCount) ||
        typeof raw.name !== 'string' || raw.name.length > 80) throw Error('올바른 Meadow 맵 JSON 파일이 아닙니다.');
    const next=create(raw.width,raw.height,raw.name,raw.biome);
    if(next.biome==='wind_plateau'){
      if(raw.tileset!==next.tileset)return next;
      if(raw.data.some(id=>id>=16))throw Error('바람 고원 맵의 타일 번호가 올바르지 않습니다.');
    }
    if(next.biome==='wasteland'){
      if(raw.tileset!==next.tileset)return next;
      if(raw.data.some(id=>id>=16))throw Error('황무지 맵의 타일 번호가 올바르지 않습니다.');
    }
    // Earlier bog maps used grassland IDs. Replace that shared ground on import.
    if(next.biome==='bog'){
      if(raw.tileset!==next.tileset)return next;
      if(raw.data.some(id=>id>=16))throw Error('늪지 맵의 타일 번호가 올바르지 않습니다.');
    }
    if(next.biome==='burnt_forest'){
      if(raw.tileset!==next.tileset&&raw.tileset!=='../volcano/tiles32/volcano-32.webp')return next;
      if(raw.data.some(id=>id>=22))throw Error('불탄 숲 맵의 타일 번호가 올바르지 않습니다.');
      return {...next,data:raw.data.map(id=>id>=10&&id<=12?id+6:id)};
    }
    return {...next,data:[...raw.data]};
  }
  const clone = map => ({...map,data:[...map.data]});
  function put(map,x,y,id) { if(x>=0 && y>=0 && x<map.width && y<map.height) map.data[y*map.width+x]=id; }
  function line(x0,y0,x1,y1,visit) {
    let dx=Math.abs(x1-x0),dy=-Math.abs(y1-y0),sx=x0<x1?1:-1,sy=y0<y1?1:-1,err=dx+dy;
    while(true){visit(x0,y0);if(x0===x1&&y0===y1)break;const e=2*err;if(e>=dy){err+=dy;x0+=sx}if(e<=dx){err+=dx;y0+=sy}}
  }
  function fill(map,x,y,id) {
    if(x<0||y<0||x>=map.width||y>=map.height)return;
    const target=map.data[y*map.width+x];if(target===id)return;
    const stack=[y*map.width+x];map.data[stack[0]]=id;
    while(stack.length){const i=stack.pop(),cx=i%map.width,cy=Math.floor(i/map.width);
      for(const [nx,ny] of [[cx-1,cy],[cx+1,cy],[cx,cy-1],[cx,cy+1]]){
        if(nx<0||ny<0||nx>=map.width||ny>=map.height)continue;
        const j=ny*map.width+nx;if(map.data[j]===target){map.data[j]=id;stack.push(j)}
      }
    }
  }
  function randomize(map, tiles, random = Math.random) {
    const families = new Map();
    for(const tile of tiles){
      if(tile.id===0||tile.hidden)continue;
      if(!families.has(tile.family))families.set(tile.family,[]);
      families.get(tile.family).push(tile.id);
    }
    const groups=[...families.values()], next=clone(map);
    next.data=map.data.map(()=>{
      if(!groups.length||random()<.65)return 0;
      const variants=groups[Math.floor(random()*groups.length)];
      return variants[Math.floor(random()*variants.length)];
    });
    return next;
  }
  function resize(map,width,height) {
    const next=create(width,height,map.name,map.biome);
    for(let y=0;y<Math.min(height,map.height);y++)for(let x=0;x<Math.min(width,map.width);x++)next.data[y*width+x]=map.data[y*map.width+x];
    return next;
  }
  class History {
    constructor(){this.past=[];this.future=[]}
    commit(before,after){if(JSON.stringify(before)===JSON.stringify(after))return false;this.past.push(clone(before));if(this.past.length>80)this.past.shift();this.future=[];return true}
    undo(map){if(!this.past.length)return map;this.future.push(clone(map));return this.past.pop()}
    redo(map){if(!this.future.length)return map;this.past.push(clone(map));return this.future.pop()}
  }
  return {biomes,create,validate,clone,put,line,fill,randomize,resize,History};
})();
if(typeof module!=='undefined')module.exports=MeadowModel;
