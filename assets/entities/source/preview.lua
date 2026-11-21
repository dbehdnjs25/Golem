local root=app.params.root or "C:/Project/pygame_project/assets/entities"
local files={"source/style-reference","player","wolf","rabbit","golem","burnt_forest_golem","snowfield_golem","wind_plateau_golem"}
local sprite=Sprite(320,208,ColorMode.RGB)
local canvas=Image(320,208,ColorMode.RGB)
local pc=app.pixelColor
for p in canvas:pixels() do
  local shade=(math.floor(p.x/8)+math.floor(p.y/8))%2==0 and 53 or 60
  p(pc.rgba(shade,shade+3,shade,255))
end
for i,key in ipairs(files) do
  local source=app.open(root.."/"..key..".png")
  local image=Image(source.spec); image:drawSprite(source,1)
  local col,row=(i-1)%4,math.floor((i-1)/4)
  canvas:drawImage(image,Point(col*80+math.floor((80-image.width)/2),row*104+94-image.height))
  source:close()
end
sprite:newCel(sprite.layers[1],1,canvas,Point(0,0))
sprite:saveCopyAs(root.."/source/preview-native.png")
sprite:close()
