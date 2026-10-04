"""Vorgerechnete Messreihe (data/rsv_results.json, erzeugt mit tools/sweep.py): Auswertung je Variante. Die App rechnet sie nie live."""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

import rsv_constants as C

ROOT = Path(__file__).resolve().parent
KEYS = ("none", "prop", "risk", "saa", "saa_blind")


def load_results(path=None) -> dict:
    return json.loads(Path(path or ROOT / C.RESULTS_FILE).read_text(encoding="utf-8"))


def mean_se(xs) -> tuple:
    xs = list(xs)
    return st.mean(xs), (st.stdev(xs) / len(xs) ** 0.5 if len(xs) > 1 else float("nan"))


def rows_of(res: dict, variant: str) -> list:
    return [r for r in res["rows"] if r["variant"] == variant]


def centroid(alloc: list) -> float:
    """Schwerpunkt der Reserve auf der Strecke: 0 = ganz am Anfang, 1 = ganz am Ende (Abschnitt k zählt als k / (n - 1))."""
    total = sum(alloc)
    n = len(alloc)
    return sum(k * a for k, a in enumerate(alloc)) / total / (n - 1) if total else float("nan")


def window_share(alloc: list, w0: int) -> float:
    """Anteil der Reserve, der in den vier Abschnitten des Störungslagen-Fensters steht."""
    total = sum(alloc)
    return sum(alloc[w0:w0 + C.SHOCK_WINDOW]) / total if total else float("nan")


def summary(res: dict, variant: str) -> dict:
    rows = rows_of(res, variant)
    out = {"n": len(rows), "B": st.mean(r["B"] for r in rows)}
    keys = [k for k in KEYS if k in rows[0]["methods"]]
    for k in keys:
        out[f"delay_{k}"], out[f"delay_{k}_se"] = mean_se(r["methods"][k]["delay"] for r in rows)
        out[f"punct_{k}"], out[f"punct_{k}_se"] = mean_se(100 * r["methods"][k]["punct"] for r in rows)
    out["gain_saa"], out["gain_saa_se"] = mean_se(100 * (1 - r["methods"]["saa"]["delay"] / r["methods"]["prop"]["delay"]) for r in rows)
    out["over_prop"], out["over_prop_se"] = mean_se(100 * (r["methods"]["prop"]["delay"] / r["methods"]["saa"]["delay"] - 1) for r in rows)
    out["over_risk"], out["over_risk_se"] = mean_se(100 * (r["methods"]["risk"]["delay"] / r["methods"]["saa"]["delay"] - 1) for r in rows)
    out["gain_none_share"] = st.mean((r["methods"]["none"]["delay"] - r["methods"]["prop"]["delay"]) / (r["methods"]["none"]["delay"] - r["methods"]["saa"]["delay"]) for r in rows)
    out["zero_share"] = st.mean(r["n_zero"] / len(r["methods"]["saa"]["alloc"]) for r in rows)
    out["centroid_saa"], out["centroid_saa_se"] = mean_se(centroid(r["methods"]["saa"]["alloc"]) for r in rows)
    out["centroid_prop"] = st.mean(centroid(r["methods"]["prop"]["alloc"]) for r in rows)
    out["optimism"], out["optimism_se"] = mean_se(100 * (r["methods"]["saa"]["delay"] - r["plan_objective"]) / r["methods"]["saa"]["delay"] for r in rows)
    if "saa_blind" in keys:
        out["blind_loss"], out["blind_loss_se"] = mean_se(100 * (r["methods"]["saa_blind"]["delay"] / r["methods"]["saa"]["delay"] - 1) for r in rows)
        for k in ("prop", "saa", "saa_blind"):
            out[f"window_{k}"] = st.mean(window_share(r["methods"][k]["alloc"], r["w0"]) for r in rows)
    return out


def all_variants(res: dict) -> list:
    spec = {v[0]: v for v in C.SWEEP_VARIANTS}
    return [{"name": name, "B_pct": spec[name][1], "data": spec[name][7], **summary(res, name)} for name in res["meta"]["variants"]]


def mean_allocation(res: dict, variant: str, key: str) -> list:
    """Mittlerer Anteil des Budgets je Abschnittsposition (Mittel über die Strecken)."""
    rows = rows_of(res, variant)
    n = len(rows[0]["methods"][key]["alloc"])
    return [st.mean(r["methods"][key]["alloc"][k] / r["B"] for r in rows) for k in range(n)]


def variant_name(settings: dict):
    """Welche Messreihen-Variante entspricht den Reglern genau (Seed und Anzeigewahl gehören nicht dazu)? None, wenn keine."""
    key = (settings["budget"], settings["trains"], settings["gap"], settings["score"], settings["share"], settings["corr"], settings["data"])
    return {(b, t, g, s, sh, co, da): name for name, b, t, g, s, sh, co, da in C.SWEEP_VARIANTS}.get(key)
