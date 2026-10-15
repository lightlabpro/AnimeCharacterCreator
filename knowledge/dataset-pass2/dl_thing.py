import json, os, urllib.request, hashlib, time
D = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(D, "stl"); os.makedirs(out, exist_ok=True)
log = open(os.path.join(D, "dl_thing_log.txt"), "a")
for x in json.load(open(os.path.join(D, "thing_dl.json"))):
    p = os.path.join(out, "%s_%s_%s" % (x["thing"], x["fid"], x["fn"]))
    if os.path.exists(p):
        continue
    for url in ("https://www.thingiverse.com/download:%s" % x["fid"],):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research measurement script)"})
            data = urllib.request.urlopen(req, timeout=120).read()
            ok = hashlib.sha256(data).hexdigest() == x["sha256"]
            open(p, "wb").write(data)
            log.write("%s %d bytes sha_ok=%s\n" % (x["fn"], len(data), ok)); log.flush()
        except Exception as e:
            log.write("%s FAIL %r\n" % (x["fn"], e)); log.flush()
        time.sleep(1.0)
open(os.path.join(D, "dl_thing_done.txt"), "w").write("done")
