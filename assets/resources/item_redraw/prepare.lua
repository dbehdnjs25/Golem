-- Export this new batch only. Never overwrite a hand-edited sprite or PNG.
-- Run: aseprite -b --script assets/resources/item_redraw/prepare.lua
local root = app.params.root or "C:/Project/pygame_project/assets/resources/item_redraw"
local pc = app.pixelColor
local outline = {48, 48, 36}
local specs = {
  {"core_shard",48,48,{teal={"6FAF9D","B9D8B1","42776F"},ice={"83B9C5","C8E4D9","527D94"}}},
  {"twig",48,48,{wood={"987148","C2A16B","624D35"}}},
  {"pebble",48,48,{stone={"898777","BCB89B","585D50"}}},
  {"grass",48,48,{green={"78914F","B2BC79","4A613C"}}},
  {"charcoal",48,48,{black={"55544E","827D6A","363C35"}}},
  {"copper_ingot",48,48,{copper={"B77C50","E0AC72","79543B"}}},
  {"iron_ingot",48,48,{iron={"9AABA6","D1D4BE","627672"}}},
  {"gold_ingot",48,48,{gold={"C9A64E","EDD484","897038"}}},
  {"brass_ingot",48,48,{brass={"AD9757","D6C486","756941"}}},
  {"steel_ingot",48,48,{steel={"788B94","B4C2C1","4D606A"}}},
  {"obsidian",48,48,{violet={"826887","B8A1BB","524359"},black={"55544E","827D6A","363C35"}}},
  {"obsidian_stone",48,48,{stone={"898777","BCB89B","585D50"},violet={"826887","B8A1BB","524359"},black={"55544E","827D6A","363C35"}}},
  {"frost_crystal",48,48,{ice={"83B9C5","C8E4D9","527D94"}}},
  {"weathered_stone",48,48,{stone={"898777","BCB89B","585D50"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"bog_moss",48,48,{green={"78914F","B2BC79","4A613C"},wood={"987148","C2A16B","624D35"}}},
  {"thunder_stone",48,48,{gold={"C9A64E","EDD484","897038"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"crude_axe",48,48,{wood={"987148","C2A16B","624D35"},stone={"898777","BCB89B","585D50"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"wood_pick",48,48,{wood={"987148","C2A16B","624D35"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"stone_pick",48,48,{wood={"987148","C2A16B","624D35"},stone={"898777","BCB89B","585D50"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"copper_pick",48,48,{wood={"987148","C2A16B","624D35"},copper={"B77C50","E0AC72","79543B"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"iron_pick",48,48,{wood={"987148","C2A16B","624D35"},iron={"9AABA6","D1D4BE","627672"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"gold_pick",48,48,{wood={"987148","C2A16B","624D35"},gold={"C9A64E","EDD484","897038"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"brass_pick",48,48,{wood={"987148","C2A16B","624D35"},brass={"AD9757","D6C486","756941"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"steel_pick",48,48,{wood={"987148","C2A16B","624D35"},steel={"788B94","B4C2C1","4D606A"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"wood_axe",48,48,{wood={"987148","C2A16B","624D35"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"stone_axe",48,48,{wood={"987148","C2A16B","624D35"},stone={"898777","BCB89B","585D50"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"copper_axe",48,48,{wood={"987148","C2A16B","624D35"},copper={"B77C50","E0AC72","79543B"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"iron_axe",48,48,{wood={"987148","C2A16B","624D35"},iron={"9AABA6","D1D4BE","627672"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"gold_axe",48,48,{wood={"987148","C2A16B","624D35"},gold={"C9A64E","EDD484","897038"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"brass_axe",48,48,{wood={"987148","C2A16B","624D35"},brass={"AD9757","D6C486","756941"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"steel_axe",48,48,{wood={"987148","C2A16B","624D35"},steel={"788B94","B4C2C1","4D606A"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"bench",48,48,{wood={"987148","C2A16B","624D35"},iron={"9AABA6","D1D4BE","627672"}}},
  {"smelter",48,48,{stone={"898777","BCB89B","585D50"},black={"55544E","827D6A","363C35"},ember={"CC803B","EFBE69","895133"}}},
  {"hearth",48,48,{stone={"898777","BCB89B","585D50"},black={"55544E","827D6A","363C35"},ember={"CC803B","EFBE69","895133"}}},
  {"fine_bench",48,48,{wood={"987148","C2A16B","624D35"},iron={"9AABA6","D1D4BE","627672"},brass={"AD9757","D6C486","756941"}}},
  {"blast_furnace",48,48,{steel={"788B94","B4C2C1","4D606A"},copper={"B77C50","E0AC72","79543B"},ember={"CC803B","EFBE69","895133"}}},
  {"burnt_forest_detector",48,48,{wood={"987148","C2A16B","624D35"},brass={"AD9757","D6C486","756941"},ember={"CC803B","EFBE69","895133"}}},
  {"snowfield_detector",48,48,{wood={"987148","C2A16B","624D35"},brass={"AD9757","D6C486","756941"},ice={"83B9C5","C8E4D9","527D94"}}},
  {"wind_detector",48,48,{wood={"987148","C2A16B","624D35"},brass={"AD9757","D6C486","756941"},teal={"6FAF9D","B9D8B1","42776F"}}},
  {"bog_detector",48,48,{wood={"987148","C2A16B","624D35"},brass={"AD9757","D6C486","756941"},green={"78914F","B2BC79","4A613C"}}},
  {"wasteland_detector",48,48,{wood={"987148","C2A16B","624D35"},gold={"C9A64E","EDD484","897038"},ice={"83B9C5","C8E4D9","527D94"}}},
  {"staff",48,48,{wood={"987148","C2A16B","624D35"},violet={"826887","B8A1BB","524359"},green={"78914F","B2BC79","4A613C"}}},
  {"worn_pack",48,48,{wood={"987148","C2A16B","624D35"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"leather_pack",48,48,{wood={"987148","C2A16B","624D35"},brass={"AD9757","D6C486","756941"}}},
  {"hide",48,48,{wood={"987148","C2A16B","624D35"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"raw_meat",48,48,{red={"B46A65","DEA18A","794A48"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"cooked_meat",48,48,{wood={"987148","C2A16B","624D35"},cream={"C1B38C","E7DBB5","8C8165"}}},
  {"potion",48,48,{rose={"B5687E","DFA2AA","7D465F"},ice={"83B9C5","C8E4D9","527D94"},wood={"987148","C2A16B","624D35"}}},
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
  assert(not exists(root.."/final/"..spec[1]..".png"),"Refusing to overwrite PNG: "..spec[1])
  assert(not exists(root.."/final/"..spec[1]..".aseprite"),"Refusing to overwrite Aseprite: "..spec[1])
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
  sprite:saveAs(root.."/final/"..key..".aseprite")
  sprite:saveCopyAs(root.."/final/"..key..".png")
  print(key..": "..w.."x"..h..", "..#colors.." monochrome layers")
  sprite:close()
end
