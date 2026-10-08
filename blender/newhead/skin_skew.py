import sys, numpy as np
d=np.load(sys.argv[1]); V=d["V"]; PL,PS=d["PL"],d["PS"]
faces=[]; o=0
for n in PS: faces.append(PL[o:o+n]); o+=n
# connected components by shared verts
parent=list(range(len(V)))
def f_(x):
    while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
    return x
for f in faces:
    r=f_(f[0])
    for v in f[1:]: parent[f_(v)]=r
comp=np.array([f_(f[0]) for f in faces]); main=np.bincount(comp).argmax()
def skew(p):
    e=[p[(k+1)%4]-p[k] for k in range(4)]; L=[np.linalg.norm(x) for x in e]
    return max(abs(np.degrees(np.arccos(np.clip(np.dot(-e[k],e[(k+1)%4])/(L[k]*L[(k+1)%4]+1e-12),-1,1)))-90) for k in range(4))
sk=np.array([skew(V[f]) for f,c in zip(faces,comp) if len(f)==4 and c==main and V[f][:,2].mean()>1.474])
ek=np.array([skew(V[f]) for f,c in zip(faces,comp) if len(f)==4 and c!=main])
print("skin quads",len(sk),"skew p95 %.1f p90 %.1f median %.1f"%(np.percentile(sk,95),np.percentile(sk,90),np.median(sk)), "| ear quads",len(ek),"p95 %.1f"%np.percentile(ek,95) if len(ek) else "")
