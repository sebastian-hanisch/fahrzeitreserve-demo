import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import rsv_constants as C, rsv_model as M, rsv_saa as S
from rsv_rng import SplitMix64, Stream
r = SplitMix64(7); st = Stream(7)
print("stream==scalar", [r.next() for _ in range(5)] == [int(x) for x in st.raw(5)])
t0 = time.time()
gaps = []; ints = 0
for seed in range(100, 120):
    cfg = M.make_config(seed)
    B = M.budget_units(cfg, 5); g = M.gap_vector(cfg, 2); w = M.score_weights("alle", cfg["n"])
    Etr = M.disturbances(cfg, 400, 5, "aus", C.TRAIN_SEED_OFFSET + seed)
    Ete = M.disturbances(cfg, C.TEST_SCENARIOS, 5, "aus", C.TEST_SEED_OFFSET + seed)
    lo = M.floor_vector(cfg, B, 0)
    a, obj = S.optimal_reserve(Etr, g, B, w, lo)
    d = {m: M.evaluate(M.method_allocation(m, cfg, B, 0), Ete, g, w)["delay"] for m in ("prop", "risk")}
    d["saa"] = M.evaluate(a, Ete, g, w)["delay"]
    d["none"] = M.evaluate(np.zeros(cfg["n"]), Ete, g, w)["delay"]
    gaps.append((d["prop"] / d["saa"] - 1, d["risk"] / d["saa"] - 1, 1 - d["saa"] / d["prop"], d["none"], d["saa"]))
g = np.array(gaps)
print("prop über saa %.1f  risk über saa %.1f  saa senkt ggü prop %.1f  none %.2f saa %.2f" % tuple(g.mean(axis=0) * np.array([100, 100, 100, 1, 1])), "Zeit", round(time.time() - t0, 1))
