-- Export this new batch only. Never overwrite a hand-edited sprite or PNG.
-- Run: aseprite -b --script assets/resources/item_redraw/prepare.lua
local root = app.params.root or "C:/Project/pygame_project/assets/resources/compass_redraw"
local pc = app.pixelColor
local outline = {48, 48, 36}
local specs = {
  {"burnt_forest_detector",32,32,{bronze={"AD9757","D6C486","756941"},dial={"C1B38C","E7DBB5","8C8165"},needle={"CC803B","EFBE69","895133"}}},
  {"snowfield_detector",32,32,{bronze={"AD9757","D6C486","756941"},dial={"C1B38C","E7DBB5","8C8165"},needle={"83B9C5","C8E4D9","527D94"}}},
  {"wind_detector",32,32,{bronze={"AD9757","D6C486","756941"},dial={"C1B38C","E7DBB5","8C8165"},needle={"91B29B","C7D5B7","5A8375"}}},
  {"bog_detector",32,32,{bronze={"AD9757","D6C486","756941"},dial={"C1B38C","E7DBB5","8C8165"},needle={"78914F","B2BC79","4A613C"}}},
  {"wasteland_detector",32,32,{bronze={"AD9757","D6C486","756941"},dial={"C1B38C","E7DBB5","8C8165"},needle={"C9A64E","EDD484","897038"}}},
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
  assert(exists(root.."/source/"..spec[1]..".png"),"Missing generated source: "..spec[1])
  assert(not exists(root.."/final32/"..spec[1]..".png"),"Refusing to overwrite PNG: "..spec[1])
  assert(not exists(root.."/final32/"..spec[1]..".aseprite"),"Refusing to overwrite Aseprite: "..spec[1])
end
for _,spec in ipairs(specs) do
  local key,w,h,materials=table.unpack(spec)
  local src=app.open(root.."/source/"..key..".png")
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
  sprite:saveAs(root.."/final32/"..key..".aseprite")
  sprite:saveCopyAs(root.."/final32/"..key..".png")
  print(key..": "..w.."x"..h..", "..#colors.." monochrome layers")
  sprite:close()
end
