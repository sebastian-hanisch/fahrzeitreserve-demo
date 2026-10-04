"""Vorgerechnete Messreihe: je Variante 40 Strecken (Seeds 100-139), alle Verfahren, Bewertung an frischen Szenarien -> data/rsv_results.json.

  python tools/sweep.py        # einige Minuten mit 6 Prozessen
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import rsv_constants as C  # noqa: E402
import rsv_evaluation as E  # noqa: E402


def one(args):
    name, budget, trains, gap, score, share, corr, data, seed = args
    settings = {"budget": budget, "trains": trains, "gap": gap, "score": score, "share": share, "corr": corr, "data": data, "seed": seed}
    runs = [E.run_live(settings, rep=r) for r in range(C.SWEEP_REPS.get(name, 1))]          # mehrere Planungsmengen je Strecke: Mittel
    run = runs[0]
    methods = {}
    for k, v in run["results"].items():
        methods[k] = {"alloc": v["alloc"], "delay": sum(r["results"][k]["delay"] for r in runs) / len(runs), "punct": sum(r["results"][k]["punct"] for r in runs) / len(runs)}
    return {"variant": name, "seed": seed, "B": run["B"], "n_zero": sum(1 for x in run["results"]["saa"]["alloc"] if x == 0), "bott": list(run["cfg"]["bott"]), "w0": run["cfg"]["w0"],
            "plan_objective": sum(r["plan_objective"] for r in runs) / len(runs), "reps": len(runs), "methods": methods}


def main():
    t0 = time.time()
    jobs = [(name, b, tr, gap, sc, sh, co, da, seed) for name, b, tr, gap, sc, sh, co, da in C.SWEEP_VARIANTS for seed in C.SWEEP_SEEDS]
    with ProcessPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(one, jobs, chunksize=4))
    res = {"meta": {"seeds": [C.SWEEP_SEEDS.start, C.SWEEP_SEEDS.stop], "test_scenarios": C.TEST_SCENARIOS, "variants": [v[0] for v in C.SWEEP_VARIANTS]}, "rows": rows}
    out = ROOT / C.RESULTS_FILE
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, separators=(",", ":")), encoding="utf-8")
    print("geschrieben:", out, round(out.stat().st_size / 1024), "KB,", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
