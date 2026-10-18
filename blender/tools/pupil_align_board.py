"""align.py OURS.png REF.png OUT.png : scale/translate ours so its pupils land on the ref's pupils; side by side + eye/nose-mouth crops."""
import sys, numpy as np
from PIL import Image
from scipy import ndimage
def pupils(im):
    a=np.asarray(im.convert("RGB")).astype(float); r,g,b=a[...,0],a[...,1],a[...,2]
    mx=a.max(-1); mn=a.min(-1); sat=(mx-mn)/(mx+1)
    m=(sat>0.25)&(g>r+15)&(g>=b-10)&(mx<235)
    lab,n=ndimage.label(m); sizes=ndimage.sum(m,lab,range(1,n+1))
    idx=np.argsort(sizes)[::-1][:2]+1
    cs=[ndimage.center_of_mass(m,lab,i) for i in idx]
    cs=sorted(cs,key=lambda c:c[1]); return np.array([[c[1],c[0]] for c in cs])
REFP={"leo_ref_front.png":[[290,328],[512,330]],"face_leia_front.png":[[187,416],[393,416]],"face_eleanor_front.png":[[310,447],[544,450]]}
def align(ours, ref, refname=""):
    po=pupils(ours); pr=np.array(REFP[refname],float) if refname in REFP else pupils(ref)
    s=np.linalg.norm(pr[1]-pr[0])/np.linalg.norm(po[1]-po[0])
    o=ours.convert("RGB").resize((int(ours.width*s),int(ours.height*s)),Image.LANCZOS)
    c=(po.mean(0)*s); t=pr.mean(0)-c
    canvas=Image.new("RGB",ref.size,(255,255,255)); canvas.paste(o,(int(round(t[0])),int(round(t[1]))))
    return canvas, pr, po, s
if __name__=="__main__":
    ours,ref=Image.open(sys.argv[1]),Image.open(sys.argv[2]).convert("RGB")
    import os
    al,pr,po,s=align(ours,ref,os.path.basename(sys.argv[2]))
    print("ref pupils",pr.round(1),"IPD",round(np.linalg.norm(pr[1]-pr[0]),1),"scale",round(s,3))
    W,H=ref.size; ipd=np.linalg.norm(pr[1]-pr[0]); cx,cy=pr.mean(0)
    def crop(im,y0,y1,x0,x1): return im.crop((int(cx+x0*ipd),int(cy+y0*ipd),int(cx+x1*ipd),int(cy+y1*ipd)))
    top=Image.new("RGB",(W*3,H),(255,255,255)); top.paste(ref,(0,0)); top.paste(al,(W,0)); top.paste(Image.blend(ref,al,0.5),(2*W,0))
    eye=[crop(x,-0.45,0.35,-1.0,1.0) for x in (ref,al)]
    nm=[crop(x,0.2,1.5,-0.7,0.7) for x in (ref,al)]
    ew,eh=eye[0].size; nw,nh=nm[0].size
    sc=W*3/(2*ew); eye=[e.resize((int(ew*sc),int(eh*sc))) for e in eye]
    sc2=W*3/(2*nw)/1.0; nm=[e.resize((int(nw*sc2),int(nh*sc2))) for e in nm]
    out=Image.new("RGB",(W*3,H+eye[0].height+nm[0].height),(255,255,255)); out.paste(top,(0,0))
    out.paste(eye[0],(0,H)); out.paste(eye[1],(eye[0].width,H))
    out.paste(nm[0],(0,H+eye[0].height)); out.paste(nm[1],(nm[0].width,H+eye[0].height))
    out.thumbnail((1800,3000)); out.save(sys.argv[3])
