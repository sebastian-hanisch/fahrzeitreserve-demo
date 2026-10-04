"""Fehler-Einbau-Test: baut einzelne Fehler in die Module ein und prüft, ob die Tests (ohne AppTests) sie finden.

Aufruf (im Projektordner): python tools/mutation_check.py [Teilstring des Dateinamens] [--jobs N] [--indices 5,8-12] [--with-app] [--dry-run]
Jeder Mutant ersetzt genau eine Stelle; Überlebende sind entweder gleichwertig (kein sichtbarer Unterschied) oder eine Lücke der Tests. Die Kopie liegt je Mutant in einem
temporären Ordner; PYTHONDONTWRITEBYTECODE=1, damit veralteter Bytecode keine Überlebenden vortäuscht; Quelltexte als LF. Ein Mutant kann in eine Endlosschleife laufen;
nach TIMEOUT Sekunden gilt er als gefunden. `--with-app` nimmt die AppTests hinzu, `--dry-run` prüft nur, ob jede Zeichenkette genau einmal vorkommt."""
import concurrent.futures
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable
WITH_APP = "--with-app" in sys.argv
TIMEOUT = 600
TEST_ORDER = ["test_rng.py", "test_model.py", "test_results.py", "test_presets.py", "test_evaluation.py", "test_stories.py", "test_gaps.py", "test_pdf.py", "test_saa.py", "test_oracle_search.py",
              "test_claims.py"]

MUTANTS = [
    ('rsv_model.py', '    r = [C.RUN_MIN + rng.below(C.RUN_MAX - C.RUN_MIN + 1) for _ in range(n)]', '    r = [C.RUN_MIN + rng.below(C.RUN_MAX - C.RUN_MIN) for _ in range(n)]'),
    ('rsv_model.py', '        bott.append(pool.pop(rng.below(len(pool))))', '        bott.append(pool.pop(0))'),
    ('rsv_model.py', '    w0 = rng.below(n - C.SHOCK_WINDOW + 1)', '    w0 = rng.below(n - C.SHOCK_WINDOW)'),
    ('rsv_model.py', '        g[k] = 0.0', '        g[k] = 1.0'),
    ('rsv_model.py', 'C.UNITS_PER_MIN + 50) // 100)', 'C.UNITS_PER_MIN) // 100)'),
    ('rsv_model.py', '        return np.array([min(k + 1, n - k) for k in range(n)], dtype=float)', '        return np.array([min(k, n - k) for k in range(n)], dtype=float)'),
    ('rsv_model.py', '        surv = surv * (1.0 - q)', '        surv = surv * q'),
    ('rsv_model.py', '    q = 10.0 / mu_tenths', '    q = 1.0 / mu_tenths'),
    ('rsv_model.py', '    bad = day < C.CORR_PERMILLE[corr]', '    bad = day <= C.CORR_PERMILLE[corr]'),
    ('rsv_model.py', 'p[bad, :, w0:w1] * C.SHOCK_FACTOR, 600)', 'p[bad, :, w0:w1] * (C.SHOCK_FACTOR - 1), 600)'),
    ('rsv_model.py', '    occ = u_occ < p\n', '    occ = u_occ <= p\n'),
    ('rsv_model.py', 'np.array(mag_table(mu_tenths)), u, side="right")', 'np.array(mag_table(mu_tenths)), u, side="left")'),
    ('rsv_model.py', '                v = np.maximum(v, A[:, j - 1, k] - g[k])', '                v = np.maximum(v, A[:, j - 1, k] + g[k])'),
    ('rsv_model.py', '    a = np.asarray(a, dtype=float) / C.UNITS_PER_MIN', '    a = np.asarray(a, dtype=float)'),
    ('rsv_model.py', '            v = prev + E[:, j, k] - a[k]', '            v = prev + E[:, j, k] + a[k]'),
    ('rsv_model.py', '((A <= C.PUNKT + 1e-9) * wn)', '((A < C.PUNKT - 1e-9) * wn)'),
    ('rsv_model.py', '    wn = w / w.sum()', '    wn = w'),
    ('rsv_model.py', '    order = np.argsort(-(a - fl), kind="stable")', '    order = np.argsort(a - fl, kind="stable")'),
    ('rsv_model.py', '    return np.floor(share / 100.0 * B * r / r.sum() + 1e-9)', '    return np.floor(share / 100.0 * B / len(r) + 1e-9)'),
    ('rsv_model.py', '    free = B - lo.sum()', '    free = B'),
    ('rsv_model.py', '        return allocate(cfg["p"] * cfg["mu"], B, lo)', '        return allocate(cfg["p"], B, lo)'),
    ('rsv_saa.py', '_build(E * unit, g * unit, w)', '_build(E * unit, g, w)'),
    ('rsv_saa.py', '    if np.abs(a - np.round(a)).max() < 1e-6:', '    if np.abs(a - np.round(a)).max() < 0.6:'),
    ('rsv_saa.py', '    lower = np.concatenate([lo, np.zeros(nA)])', '    lower = np.concatenate([np.zeros(n), np.zeros(nA)])'),
    ('rsv_saa.py', '        return np.round(a), float(res.fun) / unit', '        return np.round(a), float(res.fun)'),
    ('rsv_saa.py', 'reshape(-1) / (S * M)])', 'reshape(-1) / S])'),
    ('rsv_saa.py', '        rows.append(r2); cols.append(n + ids - n); vals.append(np.ones(len(ids)))', '        rows.append(r2); cols.append(n + ids - 1); vals.append(np.ones(len(ids)))'),
    ('rsv_evaluation.py', '    return 100 * (1 - run["results"][key]["delay"] / run["results"][ref]["delay"])', '    return 100 * (1 - run["results"][ref]["delay"] / run["results"][key]["delay"])'),
    ('rsv_evaluation.py', '    return 100 * (run["results"][key]["delay"] / run["results"][ref]["delay"] - 1)', '    return 100 * (run["results"][key]["delay"] / run["results"][ref]["delay"])'),
    ('rsv_evaluation.py', '    if gain >= 1.0:', '    if gain >= 2.0:'),
    ('rsv_evaluation.py', '    if opt >= 5.0:', '    if opt >= 6.0:'),
    ('rsv_evaluation.py', '/ total / (n - 1) if total else float("nan")\n\n\ndef window_pct', '/ total / n if total else float("nan")\n\n\ndef window_pct'),
    ('rsv_evaluation.py', 'sum(alloc[w0:w0 + C.SHOCK_WINDOW]) / total', 'sum(alloc[w0:w0 + 3]) / total'),
    ('rsv_evaluation.py', '    lo = M.floor_vector(cfg, B, settings["share"])', '    lo = np.zeros(n)'),
    ('rsv_evaluation.py', '    if corr != "aus":', '    if corr == "aus":'),
    ('rsv_evaluation.py', '    plan = M.disturbances(cfg, S_, M_, corr, C.TRAIN_SEED_OFFSET + seed + C.REP_SEED_STEP * rep)', '    plan = M.disturbances(cfg, S_, M_, corr, C.TRAIN_SEED_OFFSET + seed)'),
    ('rsv_evaluation.py', '    elif settings["score"] == "last":', '    elif settings["score"] == "alle":'),
    ('rsv_results.py', '(st.stdev(xs) / len(xs) ** 0.5 if', '(st.stdev(xs) / len(xs) if'),
    ('rsv_results.py', '100 * (r["methods"]["prop"]["delay"] / r["methods"]["saa"]["delay"] - 1) for r in rows)\n    out["over_risk"]', '100 * (r["methods"]["saa"]["delay"] / r["methods"]["prop"]["delay"] - 1) for r in rows)\n    out["over_risk"]'),
    ('rsv_results.py', 'return sum(k * a for k, a in enumerate(alloc)) / total / (n - 1) if total else float("nan")', 'return sum(k * a for k, a in enumerate(alloc)) / total / n if total else float("nan")'),
    ('rsv_results.py', '    return sum(alloc[w0:w0 + C.SHOCK_WINDOW]) / total if total else float("nan")', '    return sum(alloc[w0:w0 + 3]) / total if total else float("nan")'),
    ('rsv_results.py', '"share"], settings["corr"], settings["data"])', '"share"], "aus", settings["data"])'),
    ('rsv_results.py', 'r["n_zero"] / len(r["methods"]["saa"]["alloc"])', 'r["n_zero"]'),
    ('rsv_results.py', '- r["plan_objective"]) / r["methods"]["saa"]["delay"] for r in rows)', '- r["plan_objective"]) / r["plan_objective"] for r in rows)'),
    ('rsv_presets.py', 'return min(options, key=lambda o: (abs(o - value), o))', 'return min(options, key=lambda o: (abs(o - value), -o))'),
    ('rsv_presets.py', '                    if value not in spec.options:', '                    if False:'),
    ('rsv_constants.py', 'SHOCK_FACTOR = 3 ', 'SHOCK_FACTOR = 2 '),
    ('rsv_constants.py', 'UNITS_PER_MIN = 10 ', 'UNITS_PER_MIN = 5 '),
    ('rsv_stories.py', 'lambda f: f["gain"] >= 10.0)', 'lambda f: f["gain"] > 10.0)'),
    ('rsv_stories.py', 'lambda f: f["window_saa"] >= 50.0)', 'lambda f: f["window_saa"] > 50.0)'),
    ('rsv_stories.py', 'lambda f: f["sweep_optimism"] > 3.0)', 'lambda f: f["sweep_optimism"] >= 3.0)'),
    ('rsv_visualization.py', 'fig.add_vrect(x0=cfg["w0"] - 0.5, x1=cfg["w0"] + C.SHOCK_WINDOW - 0.5,', 'fig.add_vrect(x0=cfg["w0"], x1=cfg["w0"] + C.SHOCK_WINDOW,'),
    ('rsv_visualization.py', 'y=[x / C.UNITS_PER_MIN for x in run["results"][key]["alloc"]]', 'y=[x for x in run["results"][key]["alloc"]]'),
    ('rsv_visualization.py', 'y=[-r["optimism"] for _, r in pts]', 'y=[r["optimism"] for _, r in pts]'),
    ('rsv_pdf_export.py', '        res = alloc[k] / UNITS\n        rows.append', '        res = alloc[k]\n        rows.append'),
]


def check_unique():
    bad = []
    for n, (name, old, new) in enumerate(MUTANTS, 1):
        text = (ROOT / name).read_bytes().decode("utf-8").replace("\r\n", "\n")
        if text.count(old) != 1:
            bad.append((n, name, old[:70], text.count(old)))
        if old == new:
            bad.append((n, name, "alt == neu", 0))
    return bad


def run_one(args):
    n, name, old, new, base = args
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"abl_mut{n}_"))
    try:
        shutil.copytree(base, tmp, dirs_exist_ok=True)
        path = tmp / name
        original = path.read_bytes().decode("utf-8")
        path.write_bytes(original.replace(old, new).encode("utf-8"))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        files = [f"tests/{f}" for f in TEST_ORDER + (["test_app.py"] if WITH_APP else [])]
        try:
            r = subprocess.run([PY, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", *files], cwd=tmp, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT)
            return n, name, old, new, r.returncode == 0, False
        except subprocess.TimeoutExpired:
            return n, name, old, new, False, True                 # Endlosschleife oder zu langsam: gilt als gefunden
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = args[0] if args else ""
    jobs = 6
    if "--jobs" in sys.argv:
        jobs = int(sys.argv[sys.argv.index("--jobs") + 1])
        only = "" if only == str(jobs) else only
    wanted = None
    if "--indices" in sys.argv:
        spec = sys.argv[sys.argv.index("--indices") + 1]
        only = "" if only == spec else only
        wanted = set()
        for part in spec.split(","):
            lo, _, hi = part.partition("-")
            wanted.update(range(int(lo), int(hi or lo) + 1))
    bad = check_unique()
    for b in bad:
        print("FEHLER (Stelle nicht eindeutig gefunden):", b)
    if "--dry-run" in sys.argv:
        print(f"{len(MUTANTS)} Mutanten, {len(bad)} Fehler in der Mutantenliste")
        return
    base = pathlib.Path(tempfile.mkdtemp(prefix="abl_mut_base_"))
    for f in ROOT.glob("*.py"):
        (base / f.name).write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    shutil.copytree(ROOT / "tests", base / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(ROOT / "README.md", base / "README.md")
    shutil.copytree(ROOT / "data", base / "data")
    for f in (base / "tests").glob("*.py"):
        f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    bad_ids = {b[0] for b in bad}
    work = [(n, name, old, new, base) for n, (name, old, new) in enumerate(MUTANTS, 1) if n not in bad_ids and (not only or only in name) and (wanted is None or n in wanted)]
    survivors, killed = [], 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        for n, name, old, new, survived, timeout in pool.map(run_one, work):
            if timeout:
                print(f"[{n:3d}] Zeitüberschreitung (als gefunden gezählt)  {name}", flush=True)
            if survived:
                survivors.append((n, name, old[:70], new[:70]))
                print(f"[{n:3d}] ÜBERLEBT  {name}: {old[:70]!r} -> {new[:70]!r}", flush=True)
            else:
                killed += 1
                print(f"[{n:3d}] gefunden  {name}", flush=True)
    print(f"\n{killed} gefunden, {len(survivors)} überlebt, {len(bad)} Fehler in der Mutantenliste")
    shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    main()
