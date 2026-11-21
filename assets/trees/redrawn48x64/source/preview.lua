local root=app.params.root or "C:/Project/pygame_project/assets/trees/redrawn48x64"
local files={"source/style-reference","bog","burnt_forest","snowfield","wind_plateau","wasteland"}
local sprite=Sprite(216,176,ColorMode.RGB)
local canvas=Image(216,176,ColorMode.RGB)
local pc=app.pixelColor
for p in canvas:pixels() do
  local shade=(math.floor(p.x/8)+math.floor(p.y/8))%2==0 and 53 or 60
  p(pc.rgba(shade,shade+3,shade,255))
end
for i,key in ipairs(files) do
  local source=app.open(root.."/"..key..".png")
  local image=Image(source.spec); image:drawSprite(source,1)
  local col,row=(i-1)%3,math.floor((i-1)/3)
  canvas:drawImage(image,Point(col*72+12,row*88+12))
  source:close()
end
sprite:newCel(sprite.layers[1],1,canvas,Point(0,0))
sprite:saveCopyAs(root.."/source/preview-native.png")
sprite:close()
