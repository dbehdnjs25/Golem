local root="C:/Project/pygame_project/assets/resources"
local pc=app.pixelColor
local function rgb(h) return pc.rgba(tonumber(h:sub(1,2),16),tonumber(h:sub(3,4),16),tonumber(h:sub(5,6),16),255) end
local ink=rgb("303024")
local wood={rgb("987148"),rgb("C2A16B"),rgb("624D35")}
local cord={rgb("A38D61"),rgb("C8B680"),rgb("746047")}
local binding=Image(32,32,ColorMode.RGB)
-- Two close turns around the socket, with shaded undersides and a small knot.
for _,p in ipairs({{11,9},{12,9},{13,8},{14,8},{15,8},
                  {12,12},{13,12},{14,11},{15,11},{16,10}}) do
 binding:drawPixel(p[1],p[2]+1,cord[3])
 binding:drawPixel(p[1],p[2],p[1]<=13 and cord[2] or cord[1])
end
binding:drawPixel(16,11,cord[1])
binding:drawPixel(16,12,cord[3])
local palette={
 crude={"99876B","C9B898","635D4D"},wood={"987148","C2A16B","624D35"},
 stone={"898777","BCB89B","585D50"},copper={"B77C50","E0AC72","79543B"},
 iron={"9AABA6","D1D4BE","627672"},gold={"C9A64E","EDD484","897038"},
 brass={"AD9757","D6C486","756941"},steel={"788B94","B4C2C1","4D606A"}
}
local handle=Image(32,32,ColorMode.RGB)
-- Recover the irregular silhouette and bark from the original crude axe.
local stickSource=app.open(root.."/item_redraw/handle_backup/crude_axe.aseprite")
local stick=Image(stickSource.spec); stick:drawSprite(stickSource,1)
local ranges={
 [3]={11,13},[4]={10,14},[5]={9,15},[6]={9,15},[7]={10,16},
 [8]={12,16},[9]={12,16},[10]={13,17},[11]={13,17},[12]={13,17},
 [13]={14,18},[14]={14,18},[15]={15,19},[16]={15,20},[17]={15,20},
 [18]={16,21},[19]={17,22},[20]={17,22},[21]={18,23},[22]={19,25},
 [23]={20,26},[24]={21,27},[25]={21,28},[26]={22,28},[27]={23,29},
 [28]={24,28}
}
for y,range in pairs(ranges) do
 for x=range[1],range[2] do
  local p=stick:getPixel(x,y)
  if pc.rgbaA(p)>0 then
   if p~=ink and p~=wood[1] and p~=wood[2] and p~=wood[3] then
    local lum=pc.rgbaR(p)*0.3+pc.rgbaG(p)*0.59+pc.rgbaB(p)*0.11
    p=wood[lum>160 and 2 or (lum<105 and 3 or 1)]
   end
   handle:drawPixel(x,y,p)
  end
 end
end
stickSource:close()
local outlined=Image(handle)
for it in handle:pixels() do
 if pc.rgbaA(it())>0 then
  for _,d in ipairs({{-1,0},{1,0},{0,-1},{0,1}}) do
   if pc.rgbaA(handle:getPixel(it.x+d[1],it.y+d[2]))==0 then
    outlined:drawPixel(it.x,it.y,ink); break
   end
  end
 end
end
handle=outlined
handle:saveAs(root.."/item_redraw/shared_handle.png")
local function loadHead(kind)
 local s=app.open(root.."/item_redraw/handle_backup/iron_"..kind..".aseprite")
 local im=Image(s.spec); im:drawSprite(s,1); s:close()
 return im
end
local heads={axe=loadHead("axe"),pick=loadHead("pick")}
local function isHead(kind,x,y)
 if kind=="axe" then return y>=6 and y<=17 and x<=16 and (y<=12 or x<=10) end
 return y>=4 and y<=19 and (y<=12 or x<=10) and not (x<=13 and y<=7)
end
for _,kind in ipairs({"axe","pick"}) do
 for _,grade in ipairs({"crude","wood","stone","copper","iron","gold","brass","steel"}) do
  if grade~="crude" or kind=="axe" then
   local key=grade.."_"..kind
   local colors={}; for i,h in ipairs(palette[grade]) do colors[i]=rgb(h) end
   local flat=Image(32,32,ColorMode.RGB)
   for it in heads[kind]:pixels() do
    local p=it()
    if pc.rgbaA(p)>0 and isHead(kind,it.x,it.y) and pc.rgbaA(handle:getPixel(it.x,it.y))==0 then
     local mapped=ink
     if p~=ink then
      local lum=pc.rgbaR(p)*0.3+pc.rgbaG(p)*0.59+pc.rgbaB(p)*0.11
      mapped=colors[lum>175 and 2 or (lum<115 and 3 or 1)]
     end
     flat:drawPixel(it.x,it.y,mapped)
    end
   end
   for it in handle:pixels() do if pc.rgbaA(it())>0 then flat:drawPixel(it.x,it.y,it()) end end
   for it in binding:pixels() do if pc.rgbaA(it())>0 then flat:drawPixel(it.x,it.y,it()) end end
   -- Finish head edges without altering any shared shaft pixel.
   local finished=Image(flat)
   for it in flat:pixels() do
    if pc.rgbaA(it())>0 and (pc.rgbaA(handle:getPixel(it.x,it.y))==0 or pc.rgbaA(binding:getPixel(it.x,it.y))>0) then
     for _,d in ipairs({{-1,0},{1,0},{0,-1},{0,1}}) do
      local x,y=it.x+d[1],it.y+d[2]
      if x<0 or y<0 or x>=32 or y>=32 or pc.rgbaA(flat:getPixel(x,y))==0 then finished:drawPixel(it.x,it.y,ink); break end
     end
    end
   end
   local images={Outline=Image(32,32,ColorMode.RGB)}
   for it in finished:pixels() do
    local p=it()
    if pc.rgbaA(p)>0 then
     local name="Outline"
     if p~=ink then
      local isHandle=pc.rgbaA(handle:getPixel(it.x,it.y))>0
      local isBinding=pc.rgbaA(binding:getPixel(it.x,it.y))>0
      local set=isBinding and cord or (isHandle and wood or colors)
      for i,c in ipairs(set) do if c==p then name=(isBinding and "Binding / " or (isHandle and "Handle / " or "Head / "))..({"Base","Highlight","Shadow"})[i]; break end end
     end
     if not images[name] then images[name]=Image(32,32,ColorMode.RGB) end
     images[name]:drawPixel(it.x,it.y,p)
    end
   end
   local sprite=Sprite(32,32,ColorMode.RGB)
   sprite.layers[1].name="Outline"; sprite:newCel(sprite.layers[1],1,images.Outline,Point(0,0))
   local names={}; for n in pairs(images) do if n~="Outline" then names[#names+1]=n end end; table.sort(names)
   for _,n in ipairs(names) do local l=sprite:newLayer(); l.name=n; sprite:newCel(l,1,images[n],Point(0,0)) end
   sprite:saveAs(root.."/items/"..key..".aseprite"); sprite:saveCopyAs(root.."/items/"..key..".png")
   sprite:saveAs(root.."/item_redraw/final32/"..key..".aseprite"); sprite:saveCopyAs(root.."/item_redraw/final32/"..key..".png")
   sprite:close()
  end
 end
end
