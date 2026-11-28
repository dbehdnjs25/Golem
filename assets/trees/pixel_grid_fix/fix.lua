-- Native 48x64 pixel edits only. No resampling of generated images.
local root="C:/Project/pygame_project/assets/trees"
local keys={"bog","burnt_forest","snowfield","wind_plateau","wasteland"}
for _,key in ipairs(keys) do
  for _,ext in ipairs({".aseprite",".png"}) do
    local existing=io.open(root.."/pixel_grid_fix/ready/"..key..ext,"rb")
    if existing then existing:close(); error("Refusing to overwrite existing ready asset: "..key..ext) end
  end
end
local log=assert(io.open(root.."/pixel_grid_fix/changes.txt","w"))
local pc=app.pixelColor
local base=app.open("C:/Project/pygame_project/assets/grassland/objects/tree_base.aseprite")
local grid=base.gridBounds
base:close()
for _,key in ipairs(keys) do
  local src=app.open(root.."/redrawn48x64/"..key..".aseprite")
  assert(src.width==48 and src.height==64)
  local labels,colors,names,materials={},{},{},{}
  for i,layer in ipairs(src.layers) do
    names[i]=layer.name
    materials[i]=layer.name:match("^(.-) / ") or layer.name
    local cel=layer:cel(1)
    if cel then
      for p in cel.image:pixels() do
        if pc.rgbaA(p())>0 then
          local at=(p.y+cel.position.y)*48+p.x+cel.position.x
          assert(not labels[at],"Overlapping source layers")
          labels[at]=i
          if colors[i] then assert(colors[i]==p(),"Source layer not monochrome") end
          colors[i]=p()
        end
      end
    end
  end
  src:close()
  local edits={}
  -- Consolidate isolated shade noise within the same material only.
  -- Keep all silhouettes, material boundaries, connected veins and cracks.
  for at,label in pairs(labels) do
    if label~=1 then
      local x,y=at%48,math.floor(at/48)
      local votes={}; local same=0; local total=0
      for dy=-1,1 do for dx=-1,1 do
        if not (dx==0 and dy==0) and x+dx>=0 and x+dx<48 and y+dy>=0 and y+dy<64 then
          local other=labels[(y+dy)*48+x+dx]
          if other and materials[other]==materials[label] then
            votes[other]=(votes[other] or 0)+1; total=total+1
            if other==label then same=same+1 end
          end
        end
      end end
      if same<=1 and total>=6 then
        for other,count in pairs(votes) do
          if count>=5 then edits[at]=other; break end
        end
      end
    end
  end
  local count=0
  for at,label in pairs(edits) do labels[at]=label; count=count+1 end
  local sprite=Sprite(48,64,ColorMode.INDEXED)
  sprite.gridBounds=Rectangle(grid.x,grid.y,grid.width,grid.height)
  sprite.transparentColor=0
  local palette=Palette(#names+1)
  palette:setColor(0,Color{r=0,g=0,b=0,a=0})
  for i=1,#names do
    assert(colors[i],"Empty material shade")
    local c=colors[i]
    palette:setColor(i,Color{r=pc.rgbaR(c),g=pc.rgbaG(c),b=pc.rgbaB(c),a=255})
  end
  sprite:setPalette(palette)
  for i,name in ipairs(names) do
    local layer=i==1 and sprite.layers[1] or sprite:newLayer()
    layer.name=name
    local image=Image(48,64,ColorMode.INDEXED)
    image:clear(0)
    for at,label in pairs(labels) do
      if label==i then image:drawPixel(at%48,math.floor(at/48),i) end
    end
    sprite:newCel(layer,1,image,Point(0,0))
  end
  sprite:saveAs(root.."/pixel_grid_fix/ready/"..key..".aseprite")
  sprite:saveCopyAs(root.."/pixel_grid_fix/ready/"..key..".png")
  log:write(key..": "..count.." shade pixels regrouped, "..#names.." opaque palette colors, grid "..grid.width.."x"..grid.height.."\n")
  sprite:close()
end
log:close()
