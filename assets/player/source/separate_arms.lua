local root="C:/Project/pygame_project/assets/player"
local pc=app.pixelColor
local palette={
 pc.rgba(48,49,52,255),pc.rgba(244,245,244,255),
 pc.rgba(255,255,255,255),pc.rgba(207,215,221,255)
}
local ink,base,light,shade=table.unpack(palette)
local names={"down","up","left","right"}
local sprite=app.open(root.."/source/before_arms.aseprite")
local sheet=Image(128,32,ColorMode.RGB)
local preview=Image(640,216,ColorMode.RGB)
preview:clear(pc.rgba(109,127,112,255))
local function arm(im,x)
 for y=21,25 do
  local l,r=x,x+3
  if y==21 or y==25 then l=x+1; r=x+2 end
  for xx=l,r do
   local p=ink
   if y>21 and y<25 and xx>l and xx<r then p=xx==x+1 and light or shade end
   im:drawPixel(xx,y,p)
  end
 end
end
for i,name in ipairs(names) do
 local im=Image(sprite.spec); im:drawSprite(sprite,i)
 -- Remove attached arms and restore a simple uninterrupted torso contour.
 for y=20,26 do for x=0,31 do im:drawPixel(x,y,0) end end
 for y=20,26 do
  local l,r
  if i<=2 then
   l,r=11,20
   if y==20 then l,r=12,19 end
  else
   l,r=12,18
   if y==20 or y==26 then l,r=13,17 end
  end
  for x=l,r do
   local p=(x==l or x==r) and ink or (x>=r-2 and shade or base)
   im:drawPixel(x,y,p)
  end
 end
 if i<=2 then arm(im,6); arm(im,22)
 elseif i==3 then arm(im,21)
 else arm(im,7) end
 local images={}; for j=1,4 do images[j]=Image(32,32,ColorMode.RGB) end
 for it in im:pixels() do
  local p=it()
  if pc.rgbaA(p)>0 then
   for j,c in ipairs(palette) do if p==c then images[j]:drawPixel(it.x,it.y,p); break end end
   sheet:drawPixel((i-1)*32+it.x,it.y,p)
   for dy=0,3 do for dx=0,3 do preview:drawPixel((i-1)*160+16+it.x*4+dx,8+it.y*4+dy,p) end end
   preview:drawPixel((i-1)*160+64+it.x,168+it.y,p)
  end
 end
 for j=1,4 do
  local cel=sprite.layers[j]:cel(i)
  cel.image=images[j]; cel.position=Point(0,0)
 end
 im:saveAs(root.."/player_"..name..".png")
 local single=Sprite(32,32,ColorMode.RGB)
 for j=1,4 do
  local l=j==1 and single.layers[1] or single:newLayer()
  l.name=sprite.layers[j].name; single:newCel(l,1,images[j],Point(0,0))
 end
 single:saveAs(root.."/player_"..name..".aseprite"); single:close()
end
sprite:saveAs(root.."/player.aseprite")
sheet:saveAs(root.."/player_sheet.png")
preview:saveAs(root.."/preview.png")
sprite:close()
