local root="C:/Project/pygame_project/assets/resources/compass_redraw"
local keys={"burnt_forest_detector","snowfield_detector","wind_detector","bog_detector","wasteland_detector"}
local board=Image(800,200,ColorMode.RGB)
board:clear(app.pixelColor.rgba(207,207,181,255))
for i,key in ipairs(keys) do
 local sprite=app.open(root.."/final32/"..key..".aseprite")
 local im=Image(sprite.spec); im:drawSprite(sprite,1)
 for it in im:pixels() do
  if app.pixelColor.rgbaA(it())>0 then
   for dy=0,3 do for dx=0,3 do
    board:drawPixel((i-1)*160+16+it.x*4+dx,8+it.y*4+dy,it())
   end end
   board:drawPixel((i-1)*160+64+it.x,152+it.y,it())
  end
 end
 sprite:close()
end
board:saveAs(root.."/preview.png")
