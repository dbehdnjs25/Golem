local root="C:/Project/pygame_project/assets/resources"
local dir=root.."/item_redraw/handle_backup/"
local pc=app.pixelColor
local ink=pc.rgba(48,48,36,255)
local keys={"crude_axe","wood_axe","stone_axe","copper_axe","iron_axe","gold_axe","brass_axe","steel_axe","wood_pick","stone_pick","copper_pick","iron_pick","gold_pick","brass_pick","steel_pick"}
local function handleRegion(x,y) return y>=13 and x>=math.floor(y/2)+4 end
local function flatten(s)
 local im=Image(s.spec); im:drawSprite(s,1); return im
end
local ref=app.open(dir.."iron_axe.aseprite")
local refImage=flatten(ref)
local handle=Image(32,32,ColorMode.RGB)
for it in refImage:pixels() do
 if handleRegion(it.x,it.y) then handle:drawPixel(it.x,it.y,it()) end
end
ref:close()
-- Give the shared handle its own finished outline, including the joint.
local function edge(im,x,y)
 for _,d in ipairs({{-1,0},{1,0},{0,-1},{0,1}}) do
  local nx,ny=x+d[1],y+d[2]
  if nx<0 or ny<0 or nx>=32 or ny>=32 or pc.rgbaA(im:getPixel(nx,ny))==0 then return true end
 end
 return false
end
local finishedHandle=Image(handle)
for it in handle:pixels() do
 if pc.rgbaA(it())>0 and edge(handle,it.x,it.y) then finishedHandle:drawPixel(it.x,it.y,ink) end
end
finishedHandle:saveAs(root.."/item_redraw/shared_handle.png")
for _,key in ipairs(keys) do
 local source=app.open(dir..key..".aseprite")
 local flat=flatten(source)
 local palette={}
 for _,layer in ipairs(source.layers) do
  local cel=layer:cel(1)
  if cel then for it in cel.image:pixels() do
   if pc.rgbaA(it())>0 then palette[it()]="Head / "..layer.name end
  end end
 end
 for y=0,31 do for x=0,31 do
  if handleRegion(x,y) then flat:drawPixel(x,y,finishedHandle:getPixel(x,y)) end
 end end
 local composite=Image(flat)
 for it in flat:pixels() do
  if pc.rgbaA(it())>0 and not handleRegion(it.x,it.y) and edge(flat,it.x,it.y) then
   composite:drawPixel(it.x,it.y,ink)
  end
 end
 local images={Outline=Image(32,32,ColorMode.RGB)}
 local handleNames={
  [pc.rgba(152,113,72,255)]="Handle / Base",
  [pc.rgba(194,161,107,255)]="Handle / Highlight",
  [pc.rgba(98,77,53,255)]="Handle / Shadow"
 }
 for it in composite:pixels() do
  local p=it()
  if pc.rgbaA(p)>0 then
   local name=p==ink and "Outline" or
    (handleRegion(it.x,it.y) and assert(handleNames[p],"Unexpected handle color") or palette[p])
   assert(name,"Missing color layer")
   if not images[name] then images[name]=Image(32,32,ColorMode.RGB) end
   images[name]:drawPixel(it.x,it.y,p)
  end
 end
 source:close()
 local sprite=Sprite(32,32,ColorMode.RGB)
 sprite.layers[1].name="Outline"
 sprite:newCel(sprite.layers[1],1,images.Outline,Point(0,0))
 local names={}
 for n in pairs(images) do if n~="Outline" then names[#names+1]=n end end
 table.sort(names)
 for _,n in ipairs(names) do
  local layer=sprite:newLayer(); layer.name=n
  sprite:newCel(layer,1,images[n],Point(0,0))
 end
 sprite:saveAs(root.."/items/"..key..".aseprite")
 sprite:saveCopyAs(root.."/items/"..key..".png")
 sprite:saveAs(root.."/item_redraw/final32/"..key..".aseprite")
 sprite:saveCopyAs(root.."/item_redraw/final32/"..key..".png")
 sprite:close()
 print(key)
end
