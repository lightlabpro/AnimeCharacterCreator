import sys, json, numpy as np
sys.path.insert(0, "/tmp/claude-0/-home-claude-animecharactercreator/464105bc-a977-5cf5-aba4-7fc9139186c6/scratchpad/aud"); sys.path.insert(0, "/home/claude/acc_upbeat")
import head_audit as HA
from blender.validators import topology
npz=sys.argv[1]; out=sys.argv[2]
d=np.load(npz); V=d["V"]; PL,PS=d["PL"],d["PS"]
faces=[]; o=0
for n in PS: faces.append(list(PL[o:o+n])); o+=n
T=np.array([(f[0],f[k],f[k+1]) for f in faces for k in range(1,len(f)-1)])
top=float(V[:,2].max()); chin=1.4826
keep=V[:,2]>chin-0.08; Tk=T[keep[T].all(1)]
prof=HA.profile_from_mesh(V,Tk.tolist(),top,chin,-1)
bands=json.load(open("/tmp/claude-0/-home-claude-animecharactercreator/464105bc-a977-5cf5-aba4-7fc9139186c6/scratchpad/knowledge/head-targets-dataset.json"))["head"]
br=HA.band_report(prof,bands)
# head-region quads (above the chin - 0.1H), the ear shells excluded from the skin stats
hf=[f for f in faces if V[f][:,2].mean()>chin-0.03 and len(f)>=3]
used=sorted({i for f in hf for i in f}); rm={v:k for k,v in enumerate(used)}
st=topology.stats(V[used],[[rm[i] for i in f] for f in hf])
res={"bands_outside":br["outside"],"rows":br["rows"],"profile":prof,
     "topology":{k:v for k,v in st.items() if k!="poles"},"head_faces":len(hf),"top":top,"chin":chin}
json.dump(res,open(out,"w"),indent=1)
print("bands outside:",br["outside"] or "none")
print({k:(round(v,3) if isinstance(v,float) else v) for k,v in res["topology"].items() if k!="valence_hist"}, "head faces",len(hf))
