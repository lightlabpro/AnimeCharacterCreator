import numpy as np, sys
from PIL import Image, ImageDraw
from clay import render
BOX=(-0.72,0.72,-0.12,1.32); SZ=500
def outline(nm,yaw):
    d=np.load(nm+".npz"); img=render(d["v"],d["f"],yaw,SZ,BOX)
    bg=(np.abs(img.astype(int)-np.array([237,237,242])).sum(-1)<6)
    m=~bg; H,W=m.shape
    L=np.full(H,np.nan); R=np.full(H,np.nan)
    for y in range(H):
        xs=np.where(m[y])[0]
        if len(xs): L[y]=xs.min(); R[y]=xs.max()
    sx=(BOX[1]-BOX[0])/(W-1); hs=BOX[2]+np.arange(H)*(BOX[3]-BOX[2])/(H-1)
    return hs, BOX[0]+L*sx, BOX[0]+R*sx
names=sys.argv[1:]
O={(n,y):outline(n,y) for n in names for y in (0,90)}
np.save("sil.npy",{f"{k[0]}|{k[1]}":v for k,v in O.items()},allow_pickle=True)
W,Hh=700,760; img=Image.new("RGB",(W*2,Hh),"white"); d=ImageDraw.Draw(img)
def P(x,h,ox): return (ox+W/2+x*420, 30+(h+0.1)*480)
for n in names:
    col=(200,30,30) if n=="ours_v6g" else ((240,150,40) if n=="ours_v5f" else (150,150,150)); wd=3 if n.startswith("ours") else 1
    for yaw,ox in ((90,0),(0,W)):
        hs,L,R=O[(n,yaw)]
        for arr in (L,R):
            pts=[P(arr[j],hs[j],ox) for j in range(len(hs)) if not np.isnan(arr[j]) and hs[j]<1.12]
            if len(pts)>1: d.line(pts,fill=col,width=wd)
for h in (0,0.25,0.5,0.75,1.0):
    y=30+(h+0.1)*480; d.line([(0,y),(2*W,y)],fill=(215,215,235)); d.text((2,y-12),"h=%.2f"%h,fill=(80,80,150))
d.text((10,8),"side silhouette (face left)  grey: 5 dataset heads  orange v5f  red v6g",fill="black"); d.text((W+10,8),"front silhouette",fill="black")
img.save("silhouettes.png")
