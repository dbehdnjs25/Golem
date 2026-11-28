-- Package generated 4x5 atlases at native 32px scale; retain the original grassland art.
local root = app.params.root or 'C:/Project/pygame_project/assets/temple'
local keys = {'grassland','burnt_forest','snowfield','wind_plateau','bog','wasteland'}
if app.params.biome then keys={app.params.biome} end
local names = {'floor_plain','floor_worn','floor_cracked','floor_accent',
 'wall_north','wall_south','wall_west','wall_east',
 'corner_nw','corner_ne','corner_sw','corner_se',
 'door_north_closed','door_north_open','stairs_down','altar',
 'door_west_closed','door_west_open','door_east_closed','door_east_open'}
local board = Image(448,368,ColorMode.RGB)
board:clear(app.pixelColor.rgba(24,29,37,255))
local original = app.open(root..'/tiles32/temple-atlas.png')
local originalImage = Image(original.spec)
originalImage:drawSprite(original,1)
original:close()
for b,key in ipairs(keys) do
 local folder = root..'/'..key
 local generated = app.open(folder..'/source/generated.png')
 local src = Image(generated.spec)
 src:drawSprite(generated,1)
 local sheet = Sprite(128,160,ColorMode.RGB)
 sheet.gridBounds = Rectangle(0,0,32,32)
 for i,name in ipairs(names) do
  local col,row = (i-1)%4,math.floor((i-1)/4)
  local tile = Image(32,32,ColorMode.RGB)
  for y=0,31 do for x=0,31 do
   local pixel
   if key=='grassland' and i<=16 then
    pixel = originalImage:getPixel(col*32+x,row*32+y)
   else
    local sx=math.min(src.width-1,math.floor((col+(x+0.5)/32)*src.width/4))
    local sy=math.min(src.height-1,math.floor((row+(y+0.5)/32)*src.height/5))
    pixel=src:getPixel(sx,sy)
   end
   tile:drawPixel(x,y,pixel)
   board:drawPixel(16+((b-1)%3)*144+col*32+x,
                   16+math.floor((b-1)/3)*176+row*32+y,pixel)
  end end
  local sprite=Sprite(32,32,ColorMode.RGB)
  sprite.layers[1].name=name
  sprite:newCel(sprite.layers[1],1,tile,Point(0,0))
  sprite.gridBounds=Rectangle(0,0,32,32)
  sprite:saveAs(folder..'/tiles32/'..name..'.aseprite')
  sprite:saveCopyAs(folder..'/tiles32/'..name..'.png')
  sprite:close()
  local layer=i==1 and sheet.layers[1] or sheet:newLayer()
  layer.name=name
  sheet:newCel(layer,1,tile,Point(col*32,row*32))
 end
 sheet:saveAs(folder..'/tiles32/temple-atlas.aseprite')
 sheet:saveCopyAs(folder..'/tiles32/temple-atlas.png')
 sheet:close()
 generated:close()
 print(key..': 20 tiles packaged')
end
if not app.params.biome then board:saveAs(root..'/biomes-overview.png') end
