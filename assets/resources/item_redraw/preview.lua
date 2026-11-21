local root=app.params.root or "C:/Project/pygame_project/assets/resources/item_redraw"
local keys={"core_shard","twig","pebble","grass","charcoal","copper_ingot","iron_ingot","gold_ingot","brass_ingot","steel_ingot","obsidian","obsidian_stone","frost_crystal","weathered_stone","bog_moss","thunder_stone","crude_axe","wood_pick","stone_pick","copper_pick","iron_pick","gold_pick","brass_pick","steel_pick","wood_axe","stone_axe","copper_axe","iron_axe","gold_axe","brass_axe","steel_axe","bench","smelter","hearth","fine_bench","blast_furnace","burnt_forest_detector","snowfield_detector","wind_detector","bog_detector","wasteland_detector","staff","worn_pack","leather_pack","hide","raw_meat","cooked_meat","potion"}
local board=Image(1280,1080,ColorMode.RGB)
board:clear(app.pixelColor.rgba(207,207,181,255))
local atlas=Image(384,288,ColorMode.RGB)
local sheet=Sprite(384,288,ColorMode.RGB)
sheet.gridBounds=Rectangle(0,0,48,48)
local layerCount=0
for i,key in ipairs(keys) do
 local f=io.open(root.."/final/"..key..".png","rb")
 if f then
 f:close()
 local sprite=app.open(root.."/final/"..key..".aseprite")
 local src=Image(sprite.spec); src:drawSprite(sprite,1)
 for _,sourceLayer in ipairs(sprite.layers) do
  local cel=sourceLayer:cel(1)
  if cel then
   local layer=layerCount==0 and sheet.layers[1] or sheet:newLayer()
   layerCount=layerCount+1
   layer.name=key.." / "..sourceLayer.name
   sheet:newCel(layer,1,cel.image,Point(((i-1)%8)*48+cel.position.x,math.floor((i-1)/8)*48+cel.position.y))
  end
 end
 local cx=((i-1)%8)*160; local cy=math.floor((i-1)/8)*180
 for it in src:pixels() do
  if app.pixelColor.rgbaA(it())>0 then
   atlas:drawPixel(((i-1)%8)*48+it.x,math.floor((i-1)/8)*48+it.y,it())
   for dy=0,1 do for dx=0,1 do
    board:drawPixel(cx+32+it.x*2+dx,cy+8+it.y*2+dy,it())
   end end
  end
 end
 for y=0,31 do for x=0,31 do
  local p=src:getPixel(math.floor(x*1.5),math.floor(y*1.5))
  if app.pixelColor.rgbaA(p)>0 then board:drawPixel(cx+64+x,cy+126+y,p) end
 end end
 sprite:close()
 end
end
board:saveAs(root.."/preview.png")
atlas:saveAs(root.."/atlas.png")
sheet:saveAs(root.."/atlas.aseprite")
sheet:close()

