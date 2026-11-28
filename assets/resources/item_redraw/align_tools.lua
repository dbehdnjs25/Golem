-- Native pixel-exact mirroring, preserving all monochrome layers.
local root="C:/Project/pygame_project/assets/resources"
local keys={"crude_axe","steel_axe","wood_pick","stone_pick","iron_pick","steel_pick"}
for _,key in ipairs(keys) do
 local sprite=app.open(root.."/item_redraw/direction_backup/"..key..".aseprite")
 for _,cel in ipairs(sprite.cels) do
  local old=cel.image
  local flipped=Image(old.spec)
  for it in old:pixels() do
   flipped:drawPixel(old.width-1-it.x,it.y,it())
  end
  local pos=cel.position
  local oldWidth=old.width
  cel.image=flipped
  cel.position=Point(sprite.width-pos.x-oldWidth,pos.y)
 end
 sprite:saveAs(root.."/items/"..key..".aseprite")
 sprite:saveCopyAs(root.."/items/"..key..".png")
 sprite:saveAs(root.."/item_redraw/final32/"..key..".aseprite")
 sprite:saveCopyAs(root.."/item_redraw/final32/"..key..".png")
 sprite:close()
 print("Aligned "..key)
end
