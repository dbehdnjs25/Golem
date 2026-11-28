local root=app.params.root or "C:/Project/pygame_project/assets/resources/item_redraw"
local keys={}
for line in io.lines(root.."/keys.txt") do keys[#keys+1]=line end
local board=Image(1280,1080,ColorMode.RGB)
board:clear(app.pixelColor.rgba(207,207,181,255))
local atlas=Image(128,96,ColorMode.RGB)
local sheet=Sprite(128,96,ColorMode.RGB)
sheet.gridBounds=Rectangle(0,0,16,16)
local layerCount=0
for i,key in ipairs(keys) do
 local f=io.open(root.."/final16/"..key..".aseprite","rb")
 if f then
  f:close()
  local sprite=app.open(root.."/final16/"..key..".aseprite")
  local src=Image(sprite.spec); src:drawSprite(sprite,1)
  local ax=((i-1)%8)*16; local ay=math.floor((i-1)/8)*16
  for _,sourceLayer in ipairs(sprite.layers) do
   local cel=sourceLayer:cel(1)
   if cel then
    local layer=layerCount==0 and sheet.layers[1] or sheet:newLayer()
    layerCount=layerCount+1
    layer.name=key.." / "..sourceLayer.name
    sheet:newCel(layer,1,cel.image,Point(ax+cel.position.x,ay+cel.position.y))
   end
  end
  local cx=((i-1)%8)*160; local cy=math.floor((i-1)/8)*180
  for it in src:pixels() do
   if app.pixelColor.rgbaA(it())>0 then
    atlas:drawPixel(ax+it.x,ay+it.y,it())
    for dy=0,5 do for dx=0,5 do
     board:drawPixel(cx+32+it.x*6+dx,cy+8+it.y*6+dy,it())
    end end
    board:drawPixel(cx+72+it.x,cy+126+it.y,it())
   end
  end
  sprite:close()
 end
end
board:saveAs(root.."/preview16.png")
atlas:saveAs(root.."/atlas16.png")
sheet:saveAs(root.."/atlas16.aseprite")
sheet:close()
