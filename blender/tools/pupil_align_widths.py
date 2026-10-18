import sys, numpy as np
from PIL import Image
sys.path.insert(0,'.')
from pupil_align_board import align, REFP
R="/home/claude/acc_wizard/"
def skin(a):
    a=a.astype(int); r,g,b=a[...,0],a[...,1],a[...,2]
    return (r>150)&(r-b>35)&(r-b<110)&(g>110)&(r>g)&(g>b)
def widths(a,cx,cy,ipd,levels):
    m=skin(a); out=[]
    for t in levels:
        y=int(cy+t*ipd); row=m[y]; x=int(cx)
        if not row[x]: out.append(np.nan); continue
        l=x
        while l>0 and (row[l-1] or row[max(l-4,0):l].any()): l-=1
        r=x
        while r<len(row)-1 and (row[r+1] or row[r+1:r+5].any()): r+=1
        out.append(((r-l)/ipd, (l-cx)/ipd, (r-cx)/ipd))
    return out
ref=Image.open(R+"docs/qa/head_v2/judge/leo_ref_front.png").convert("RGB")
ours=Image.open(sys.argv[1] if len(sys.argv)>1 else R+"docs/qa/head_v2/gate/q31_h6/front.png")
al,pr,po,s=align(ours,ref,"leo_ref_front.png")
cx,cy=pr.mean(0); ipd=np.linalg.norm(pr[1]-pr[0])
L=[0.3,0.45,0.6,0.75,0.9,1.05,1.2,1.35,1.5,1.6,1.7]
for name,a in (("leo",np.asarray(ref)),("ours",np.asarray(al))):
    print(name,' '.join("%.2f:%s"%(t,("%.2f[%+.2f,%+.2f]"%w) if isinstance(w,tuple) else "nan") for t,w in zip(L,widths(a,cx,cy,ipd,L))))
