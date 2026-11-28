local root="C:/Project/pygame_project/assets/trees"
local paths={"C:/Project/pygame_project/assets/grassland/objects/tree_base.aseprite"}
for _,k in ipairs({"bog","burnt_forest","snowfield","wind_plateau","wasteland"}) do paths[#paths+1]=root.."/pixel_grid_fix/ready/"..k..".aseprite" end
local pc=app.pixelColor
local scale=4
for _,grid in ipairs({false,true}) do
  local sheet=Sprite(192*scale,160*scale,ColorMode.RGB)
  local out=Image(sheet.spec)
  out:clear(pc.rgba(54,59,55,255))
  for i,path in ipairs(paths) do
    local source=app.open(path)
    local flat=Image(source.spec); flat:drawSprite(source,1)
    local ox=((i-1)%3*64+8)*scale
    local oy=(math.floor((i-1)/3)*80+8)*scale
    for y=0,63 do for x=0,47 do
      local p=flat:getPixel(x,y)
      if source.colorMode==ColorMode.INDEXED then
        local c=source.palettes[1]:getColor(p)
        p=pc.rgba(c.red,c.green,c.blue,p==source.transparentColor and 0 or c.alpha)
      end
      local a=pc.rgbaA(p)
      for dy=0,scale-1 do for dx=0,scale-1 do
        local c=p
        if a==0 then c=pc.rgba(54,59,55,255) end
        if grid and (dx==scale-1 or dy==scale-1) then c=pc.rgba(35,39,36,255) end
        out:drawPixel(ox+x*scale+dx,oy+y*scale+dy,c)
      end end
    end end
    source:close()
  end
  sheet:newCel(sheet.layers[1],1,out,Point(0,0))
  sheet:saveCopyAs(root.."/pixel_grid_fix/"..(grid and "preview-grid.png" or "preview.png"))
  sheet:close()
end
