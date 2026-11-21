-- Export this new batch only. Never overwrite a hand-edited sprite or PNG.
-- Run: aseprite -b --script assets/entities/source/prepare.lua
local root = app.params.root or "C:/Project/pygame_project/assets/entities"
local pc = app.pixelColor
local outline = {48, 48, 36}
local specs = {
  {"player",48,64,{cloth={"74864D","A4B971","465638"},leather={"966A40","C49A60","60452F"},skin={"C69368","E3B785","916145"},hair={"795331","B1884C","503A28"}}},
  {"wolf",64,48,{fur={"89857B","B8B3A0","57594F"},cream={"C4B99B","DDD1AF","938A74"}}},
  {"rabbit",32,32,{fur={"B5A58A","D9C8A8","82765F"},ear={"AF8070","D2A08A","785B50"}}},
  {"golem",64,80,{stone={"858570","B4B297","555B4D"},moss={"70854C","A1B36A","455736"}}},
  {"burnt_forest_golem",64,80,{basalt={"57564C","85816B","373C34"},wood={"775039","A77A4E","4F3829"},ember={"CC6D32","E7A64D","91432C"}}},
  {"snowfield_golem",64,80,{stone={"798C8B","A7B8AF","4E6562"},snow={"D1D9C6","F0EFD9","9EB6AB"},ice={"8BB8BB","C3E0D2","578D99"}}},
  {"wind_plateau_golem",64,80,{stone={"92917A","C2B99A","636958"},grass={"A79458","D1BC76","736A40"},rune={"B4C6A0","D6DDB8","819877"}}},
}
local function exists(path)
  local f=io.open(path,"rb")
  if f then f:close(); return true end
  return false
end
-- Preflight the entire batch before writing anything.
for _,spec in ipairs(specs) do
  assert(exists(root.."/source/"..spec[1]..".png"),"Missing generated source: "..spec[1])
  assert(not exists(root.."/"..spec[1]..".png"),"Refusing to overwrite PNG: "..spec[1])
  assert(not exists(root.."/"..spec[1]..".aseprite"),"Refusing to overwrite Aseprite: "..spec[1])
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
  sprite:saveAs(root.."/"..key..".aseprite")
  sprite:saveCopyAs(root.."/"..key..".png")
  print(key..": "..w.."x"..h..", "..#colors.." monochrome layers")
  sprite:close()
end
