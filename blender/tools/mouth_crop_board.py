import sys
from PIL import Image
# args: out  path@cx,ey,my,cy ...   -> mouth crops (same box as judge mouth_open) side by side, 300px tall
out=sys.argv[1]; tiles=[]
for a in sys.argv[2:]:
    p,lm=a.split('@'); cx,ey,my,cy=[float(v) for v in lm.split(',')]; D=cy-ey
    im=Image.open(p).convert('RGB').resize((600,600))
    c=im.crop((int(cx-0.42*D),int(my-0.16*D),int(cx+0.42*D),int(my+0.22*D))); c=c.resize((int(300*c.size[0]/c.size[1]),300)); tiles.append(c)
W=Image.new('RGB',(sum(t.size[0] for t in tiles)+10*len(tiles),300),'white'); x=0
for t in tiles: W.paste(t,(x,0)); x+=t.size[0]+10
W.save(out)
