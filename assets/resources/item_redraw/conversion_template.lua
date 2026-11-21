-- Export this new batch only. Never overwrite a hand-edited sprite or PNG.
-- Run: aseprite -b --script assets/entities/remaining/prepare.lua
local root = app.params.root or "C:/Project/pygame_project/assets/entities"
local pc = app.pixelColor
local outline = {48, 48, 36}
local specs = {
  {"bog_golem",64,80,{stone={"74745A","A4A17B","4B5140"},moss={"6D824B","A0AC66","435735"},wood={"806344","AD8B59","554532"}}},
  {"wasteland_golem",64,80,{stone={"AD8F60","D6BD83","766146"},crystal={"75ACAC","B6D8CB","496F74"}}},
  {"burnt_lord",96,112,{basalt={"59574D","87816A","383D34"},wood={"78513A","A87A50","50392B"},ember={"CB7136","E8AD55","90452D"}}},
  {"frost_lord",96,112,{stone={"788C89","A7B6AA","4D6460"},ice={"87B4BB","C5DFD6","527E90"},snow={"CFD7C7","EEECD7","9BACAA"}}},
  {"gale_lord",96,112,{stone={"90917B","BEB99B","606957"},mint={"91B29B","C7D5B7","5A8375"},cloth={"9D9F73","D0CAA0","686E4E"}}},
  {"bog_lord",112,112,{wood={"786044","A58A5B","504331"},moss={"6B7E48","A0AB66","435533"},fungus={"A68B4D","D0B878","705C38"}}},
  {"storm_lord",96,112,{stone={"AA8C5C","D6BB83","756047"},bronze={"807047","B39A5E","554F37"},crystal={"77ACB5","C1DFD8","4A7588"}}},
}
if app.params.key then
  local chosen={}
  for _,spec in ipairs(specs) do
    if spec[1]==app.params.key then chosen[#chosen+1]=spec end
  end
  assert(#chosen==1,"Unknown entity key")
  specs=chosen
end
local function exists(path)
  local f=io.open(path,"rb")
  if f then f:close(); return true end
  return false
end
-- Preflight the entire batch before writing anything.
for _,spec in ipairs(specs) do
  assert(exists(root.."/remaining/source/"..spec[1]..".png"),"Missing generated source: "..spec[1])
  assert(not exists(root.."/"..spec[1]..".png"),"Refusing to overwrite PNG: "..spec[1])
  assert(not exists(root.."/"..spec[1]..".aseprite"),"Refusing to overwrite Aseprite: "..spec[1])
end
for _,spec in ipairs(specs) do
  local key,w,h,materials=table.unpack(spec)
  local src=app.open(root.."/remaining/source/"..key..".png")
  local input=Image(src.spec)
  input:drawSprite(src,1)
  local left,top,right,bottom=input.width,input.height,-1,-1
  for it in input:pixels() do
    if pc.rgbaA(it())>=128 then
      left=math.min(left,it.x); right=math.max(right,it.x)
      top=math.min(top,it.y); bottom=math.max(bottom,it.y)
    end
  end
  assert(right>=left,"Empty source")
  local sw,sh=right-left+1,bottom-top+1
  local scale=math.min((w-6)/sw,(h-6)/sh)
  local dw,dh=math.floor(sw*scale+0.5),math.floor(sh*scale+0.5)
  local ox,oy=math.floor((w-dw)/2),h-3-dh
  local sampled={}
  for y=0,dh-1 do for x=0,dw-1 do
    local p=input:getPixel(left+math.min(sw-1,math.floor((x+0.5)*sw/dw)),top+math.min(sh-1,math.floor((y+0.5)*sh/dh)))
    if pc.rgbaA(p)>=128 then sampled[(y+oy)*w+x+ox]=p end
  end end
  src:close()
  local colors={{name="Outline",r=outline[1],g=outline[2],b=outline[3]}}
  local names={}; for name in pairs(materials) do names[#names+1]=name end; table.sort(names)
  for _,name in ipairs(names) do
    for i,hex in ipairs(materials[name]) do
      colors[#colors+1]={name=name.." / "..({"Base","Highlight","Shadow"})[i],r=tonumber(hex:sub(1,2),16),g=tonumber(hex:sub(3,4),16),b=tonumber(hex:sub(5,6),16)}
    end
  end
  local sprite=Sprite(w,h,ColorMode.RGB)
  local images={}; local counts={}
  for i,c in ipairs(colors) do images[i]=Image(w,h,ColorMode.RGB); counts[i]=0 end
  for at,p in pairs(sampled) do
    local x,y=at%w,math.floor(at/w)
    local edge=not sampled[at-1] or not sampled[at+1] or not sampled[at-w] or not sampled[at+w]
    local selected=1
    if not edge then
      local best=math.huge
      for i,c in ipairs(colors) do
        local d=2*(pc.rgbaR(p)-c.r)^2+3*(pc.rgbaG(p)-c.g)^2+(pc.rgbaB(p)-c.b)^2
        if d<best then best=d; selected=i end
      end
    end
    local c=colors[selected]
    images[selected]:drawPixel(x,y,pc.rgba(c.r,c.g,c.b,255))
    counts[selected]=counts[selected]+1
  end
  for i,c in ipairs(colors) do
    local layer=i==1 and sprite.layers[1] or sprite:newLayer()
    layer.name=c.name
    sprite:newCel(layer,1,images[i],Point(0,0))
  end
  sprite:saveAs(root.."/"..key..".aseprite")
  sprite:saveCopyAs(root.."/"..key..".png")
  print(key..": "..w.."x"..h..", "..#colors.." monochrome layers")
  sprite:close()
end
