import sys, numpy as np
d=np.load(sys.argv[1]); V=d["V"]; PL,PS=d["PL"],d["PS"]
C=np.array([0,0,1.4826+0.45*0.262]); o=0; bad=[]
nf=0
for n in PS:
    f=PL[o:o+n]; o+=n; p=V[f]; c=p.mean(0)
    if c[2] < 1.44: continue
    nn=np.cross(p[2]-p[0], p[-1]-p[1]) if n==4 else np.cross(p[1]-p[0],p[2]-p[0])
    nn/=np.linalg.norm(nn)+1e-12; r=(c-C); r/=np.linalg.norm(r)
    nf+=1
    if nn@r < 0.0: bad.append(c)
bad=np.array(bad); print("faces",nf,"inward-facing",len(bad))
if len(bad): 
    import collections
    print(np.round(bad[np.argsort(bad[:,2])][:12],3).tolist())
