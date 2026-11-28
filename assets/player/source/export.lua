local root="C:/Project/pygame_project/assets/player"
local pc=app.pixelColor
local inputSprite=app.open(root.."/source/turnaround.png")
local input=Image(inputSprite.spec); input:drawSprite(inputSprite,1)
local cw,ch=math.floor(input.width/2),math.floor(input.height/2)
local names={"down","up","left","right"}
local bounds={}
local maxW,maxH=0,0
for i=1,4 do
 local ox=((i-1)%2)*cw; local oy=math.floor((i-1)/2)*ch
 local l,t,r,b=cw,ch,-1,-1
 for y=0,ch-1 do for x=0,cw-1 do
  if pc.rgbaA(input:getPixel(ox+x,oy+y))>=128 then
   l=math.min(l,x); t=math.min(t,y); r=math.max(r,x); b=math.max(b,y)
  end
 end end
 assert(r>=l,"Missing direction "..names[i])
 bounds[i]={ox+l,oy+t,r-l+1,b-t+1}
 maxW=math.max(maxW,r-l+1); maxH=math.max(maxH,b-t+1)
end
local scale=math.min(28/maxW,28/maxH)
local palette={
 {name="Outline and eyes",r=48,g=49,b=52},
 {name="White / Base",r=244,g=245,b=244},
 {name="White / Highlight",r=255,g=255,b=255},
 {name="White / Shadow",r=207,g=215,b=221}
}
local sprite=Sprite(32,32,ColorMode.RGB)
for i=2,4 do sprite:newEmptyFrame() end
for i,c in ipairs(palette) do
 local layer=i==1 and sprite.layers[1] or sprite:newLayer(); layer.name=c.name
end
local sheet=Image(128,32,ColorMode.RGB)
local preview=Image(640,216,ColorMode.RGB)
preview:clear(pc.rgba(109,127,112,255))
for i,name in ipairs(names) do
 local b=bounds[i]; local w,h=math.floor(b[3]*scale+0.5),math.floor(b[4]*scale+0.5)
 local ox,oy=math.floor((32-w)/2),30-h
 local sampled={}
 for y=0,h-1 do for x=0,w-1 do
  local p=input:getPixel(b[1]+math.min(b[3]-1,math.floor((x+0.5)*b[3]/w)),b[2]+math.min(b[4]-1,math.floor((y+0.5)*b[4]/h)))
  if pc.rgbaA(p)>=128 then sampled[(y+oy)*32+x+ox]=p end
 end end
 local layers={}; for c=1,4 do layers[c]=Image(32,32,ColorMode.RGB) end
 local flat=Image(32,32,ColorMode.RGB)
 for at,p in pairs(sampled) do
  local x,y=at%32,math.floor(at/32)
  local selected=1
  if sampled[at-1] and sampled[at+1] and sampled[at-32] and sampled[at+32] then
   local best=math.huge
   for j,c in ipairs(palette) do
    local d=(pc.rgbaR(p)-c.r)^2+(pc.rgbaG(p)-c.g)^2+(pc.rgbaB(p)-c.b)^2
    if d<best then best=d; selected=j end
   end
  end
  local c=palette[selected]; local color=pc.rgba(c.r,c.g,c.b,255)
  flat:drawPixel(x,y,color); layers[selected]:drawPixel(x,y,color)
  sheet:drawPixel((i-1)*32+x,y,color)
  for dy=0,3 do for dx=0,3 do preview:drawPixel((i-1)*160+16+x*4+dx,8+y*4+dy,color) end end
  preview:drawPixel((i-1)*160+64+x,168+y,color)
 end
 for j=1,4 do sprite:newCel(sprite.layers[j],sprite.frames[i],layers[j],Point(0,0)) end
 sprite.frames[i].duration=0.15
 local tag=sprite:newTag(i,i); tag.name=name
 flat:saveAs(root.."/player_"..name..".png")
 local single=Sprite(32,32,ColorMode.RGB)
 for j,c in ipairs(palette) do
  local layer=j==1 and single.layers[1] or single:newLayer(); layer.name=c.name
  single:newCel(layer,1,layers[j],Point(0,0))
 end
 single:saveAs(root.."/player_"..name..".aseprite"); single:close()
end
sprite:saveAs(root.."/player.aseprite")
sheet:saveAs(root.."/player_sheet.png")
preview:saveAs(root.."/preview.png")
sprite:close(); inputSprite:close()
