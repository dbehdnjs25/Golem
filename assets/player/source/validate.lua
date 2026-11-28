local root="C:/Project/pygame_project/assets/player"
local names={"down","up","left","right"}
local pc=app.pixelColor
local sprite=app.open(root.."/player.aseprite")
assert(sprite.width==32 and sprite.height==32 and #sprite.frames==4 and #sprite.layers==4)
assert(#sprite.tags==4)
for i,name in ipairs(names) do
 local frame=Image(sprite.spec); frame:drawSprite(sprite,i)
 local png=Image{fromFile=root.."/player_"..name..".png"}
 assert(png.width==32 and png.height==32)
 for it in png:pixels() do
  local p=it(); local alpha=pc.rgbaA(p)
  assert(alpha==0 or alpha==255)
  assert(p==frame:getPixel(it.x,it.y))
  if alpha>0 then assert(it.x>=2 and it.x<=29 and it.y>=2 and it.y<=29) end
 end
 for _,layer in ipairs(sprite.layers) do
  local cel=layer:cel(i)
  assert(cel)
  local color=nil
  for it in cel.image:pixels() do
   if pc.rgbaA(it())>0 then
    if color then assert(color==it(),"Layer is not monochrome") else color=it() end
   end
  end
 end
 print("PASS "..name..": 32x32, transparent, 4 monochrome layers, PNG matches native frame")
end
sprite:close()
