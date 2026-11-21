-- Export this new batch only. Never overwrite a hand-edited sprite or PNG.
-- Run: aseprite -b --script assets/trees/redrawn48x64/source/prepare.lua
local root = app.params.root or "C:/Project/pygame_project/assets/trees/redrawn48x64"
local pc = app.pixelColor
local outline = {48, 48, 36}
local specs = {
  {"bog",48,64,{foliage={"738344","A5AD62","485733"},bark={"82653F","B19358","51462F"}}},
  {"burnt_forest",48,64,{bark={"685043","977258","403B32"},leaves={"8B6439","B88B4B","5D4A30"}}},
  {"snowfield",48,64,{needles={"608E83","91B6A0","3E635F"},snow={"D6E4DB","F3F4DF","ABC7C7"},bark={"986E43","C39B62","654D34"}}},
  {"wind_plateau",48,64,{foliage={"718D4E","A5BC72","47643D"},bark={"9F7E4A","CEAC6A","6D5837"}}},
  {"wasteland",48,64,{bark={"B49360","DDC392","7E6745"},foliage={"B38C39","DDB961","7B6532"}}},
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
  local scale=math.min((w-4)/sw,(h-4)/sh)
  local dw,dh=math.floor(sw*scale+0.5),math.floor(sh*scale+0.5)
  local ox,oy=math.floor((w-dw)/2),h-2-dh
  local sampled={}
  for y=0,dh-1 do for x=0,dw-1 do
    local p=input:getPixel(left+math.min(sw-1,math.floor((x+0.5)*sw/dw)),top+math.min(sh-1,math.floor((y+0.5)*sh/dh)))
    if pc.rgbaA(p)>=128 then sampled[(y+oy)*w+x+ox]=p end
  end end
  src:close()
  -- Discard isolated export specks without erasing connected bark/leaf detail.
  local seen={}
  for first in pairs(sampled) do
    if not seen[first] then
      local queue={first}; seen[first]=true
      local cursor=1
      while cursor<=#queue do
        local at=queue[cursor]; cursor=cursor+1
        local x,y=at%w,math.floor(at/w)
        for dy=-1,1 do for dx=-1,1 do
          local nx,ny=x+dx,y+dy
          local nextAt=ny*w+nx
          if nx>=0 and nx<w and ny>=0 and ny<h and sampled[nextAt] and not seen[nextAt] then
            seen[nextAt]=true; queue[#queue+1]=nextAt
          end
        end end
      end
      if #queue<=2 then for _,at in ipairs(queue) do sampled[at]=nil end end
    end
  end
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
