local root=app.params.root or "C:/Project/pygame_project/assets/entities"
local files={
  root.."/../grassland/objects/tree_base.png",
  root.."/bog_golem.png",root.."/wasteland_golem.png",root.."/burnt_lord.png",
  root.."/frost_lord.png",root.."/gale_lord.png",root.."/bog_lord.png",root.."/storm_lord.png"
}
local board=Image(1440,780,ColorMode.RGB)
board:clear(app.pixelColor.rgba(207,207,181,255))
for i,path in ipairs(files) do
  local sprite=app.open(path)
  local src=Image(sprite.spec)
  src:drawSprite(sprite,1)
  local ox=((i-1)%4)*360+math.floor((360-src.width*3)/2)
  local oy=math.floor((i-1)/4)*390+360-src.height*3
  for it in src:pixels() do
    if app.pixelColor.rgbaA(it())>0 then
      for dy=0,2 do for dx=0,2 do
        board:drawPixel(ox+it.x*3+dx,oy+it.y*3+dy,it())
      end end
    end
  end
  sprite:close()
end
board:saveAs(root.."/remaining/preview.png")
