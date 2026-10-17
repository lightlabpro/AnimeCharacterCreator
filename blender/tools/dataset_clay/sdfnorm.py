import numpy as np, sys
def norm(src, dst):
    d=np.load(src); V=d["v"].astype(float); F=d["f"]
    top=V[:,2].max(); Hn=0.22
    fr=(np.abs(V[:,0])<0.03*Hn)&(V[:,1]<-0.15*Hn)&(V[:,2]<top-0.7*Hn); chin=V[fr,2].min(); H=top-chin
    P=np.stack([V[:,0]/H, V[:,1]/H, (top-V[:,2])/H],1)
    np.savez_compressed(dst, v=P.astype(np.float32), f=F[:, ::-1].astype(np.int32))
if __name__=="__main__": norm(sys.argv[1], sys.argv[2])
