"""Live-Rechnung: Reserve je Verfahren, Bewertung an frischen Szenarien, Meldungen der App."""
from __future__ import annotations

import time

import numpy as np

import rsv_constants as C
import rsv_model as M
import rsv_saa as S


def run_live(settings: dict, train: int | None = None, rep: int = 0) -> dict:
    """Strecke und Verfahren für die Einstellungen. Planungsszenarien (beobachtete Tage) kommen aus der gewählten Störungslage, die Bewertung läuft an frischen Tagen derselben Verteilung.
    Bei Störungslagen rechnet zusätzlich `saa_blind`: dasselbe Optimum, aber nach Planungstagen ohne Störungslage (es kennt die gemeinsame Störanfälligkeit nicht)."""
    t0 = time.time()
    seed, M_, corr = settings["seed"], settings["trains"], settings["corr"]
    cfg = M.make_config(seed)
    n = cfg["n"]
    B = M.budget_units(cfg, settings["budget"])
    g = M.gap_vector(cfg, settings["gap"])
    w = M.score_weights(settings["score"], n)
    lo = M.floor_vector(cfg, B, settings["share"])
    S_ = settings["data"] if train is None else train
    test = M.disturbances(cfg, C.TEST_SCENARIOS, M_, corr, C.TEST_SEED_OFFSET + seed)
    alloc = {"none": np.zeros(n), "prop": M.method_allocation("prop", cfg, B, settings["share"]), "risk": M.method_allocation("risk", cfg, B, settings["share"])}
    plan = M.disturbances(cfg, S_, M_, corr, C.TRAIN_SEED_OFFSET + seed + C.REP_SEED_STEP * rep)
    alloc["saa"], obj = S.optimal_reserve(plan, g, B, w, lo)
    if corr != "aus":
        blind = M.disturbances(cfg, S_, M_, "aus", C.TRAIN_SEED_OFFSET + seed + C.REP_SEED_STEP * rep)
        alloc["saa_blind"], _ = S.optimal_reserve(blind, g, B, w, lo)
    results = {}
    for key, a in alloc.items():
        ev = M.evaluate(a, test, g, w)
        results[key] = {"alloc": [int(x) for x in a], "delay": ev["delay"], "punct": ev["punct"], "profile": [float(x) for x in ev["profile"]]}
    return {"cfg": cfg, "corr": corr, "B": B, "results": results, "plan_objective": obj, "seconds": time.time() - t0}


def gain_pct(run: dict, key: str = "saa", ref: str = "prop") -> float:
    """Um wie viel Prozent die mittlere Verspätung von `key` unter der von `ref` liegt (Basis = Referenz)."""
    return 100 * (1 - run["results"][key]["delay"] / run["results"][ref]["delay"])


def over_pct(run: dict, key: str = "prop", ref: str = "saa") -> float:
    """Um wie viel Prozent die Verspätung von `key` über der von `ref` liegt (Basis = Referenz)."""
    return 100 * (run["results"][key]["delay"] / run["results"][ref]["delay"] - 1)


def centroid_pct(alloc) -> float:
    """Schwerpunkt der Reserve auf der Strecke in Prozent (0 = ganz am Anfang, 100 = ganz am Ende)."""
    total = sum(alloc)
    n = len(alloc)
    return 100 * sum(k * a for k, a in enumerate(alloc)) / total / (n - 1) if total else float("nan")


def window_pct(alloc, w0: int) -> float:
    """Anteil der Reserve (in Prozent) in den vier Abschnitten des Störungslagen-Fensters."""
    total = sum(alloc)
    return 100 * sum(alloc[w0:w0 + C.SHOCK_WINDOW]) / total if total else float("nan")


def optimism_pct(run: dict) -> float:
    """Selbsttäuschung des Optimums: wie viel Prozent schlechter die frischen Tage sind als die Planungstage versprachen (Basis = frische Tage)."""
    test = run["results"]["saa"]["delay"]
    return 100 * (test - run["plan_objective"]) / test


def messages(run: dict, settings: dict) -> list:
    """Meldungen der App als Liste (Zustand, Text); Zustand `success`, `info` oder `warning`."""
    out = []
    r = run["results"]
    n = run["cfg"]["n"]
    gain = gain_pct(run)
    alloc = r["saa"]["alloc"]
    used = sum(1 for x in alloc if x > 0)
    if gain >= 1.0:
        out.append(("success" if gain >= 10.0 else "info",
                    f"Das Optimum senkt die mittlere Verspätung um {gain:.0f} % gegenüber der Praxisregel ({r['prop']['delay']:.2f} auf {r['saa']['delay']:.2f} min, frische Tage). "
                    f"Es verteilt die Reserve auf {used} von {n} Abschnitten, Schwerpunkt bei {centroid_pct(alloc):.0f} % der Strecke (Praxisregel {centroid_pct(r['prop']['alloc']):.0f} %)."))
    else:
        out.append(("info", f"Praxisregel und Optimum liegen hier gleichauf ({r['prop']['delay']:.2f} gegen {r['saa']['delay']:.2f} min): Bei so wenig Reserve gibt es kaum etwas zu verteilen."))
    if settings["score"] == "ende":
        out.append(("info", f"Es zählt nur die Endankunft: Das Optimum legt {100 * sum(alloc[-2:]) / max(sum(alloc), 1):.0f} % der Reserve in die letzten beiden Abschnitte. Wo Verspätung gezählt wird, bestimmt, wo die Reserve hingehört."))
    elif settings["score"] == "last":
        out.append(("info", "Es zählt die Fahrgastlast (Mitte schwerer): Die Reserve gehört vor und in die Streckenmitte, wo die meisten Fahrgäste ankommen."))
    if "saa_blind" in r:
        w0 = run["cfg"]["w0"]
        loss = over_pct(run, "saa_blind", "saa")
        out.append(("info", f"Störungslagen: Das Optimum legt {window_pct(alloc, w0):.0f} % der Reserve in das gefährdete Fenster (Abschnitte {w0 + 1} bis {w0 + C.SHOCK_WINDOW}), die Praxisregel {window_pct(r['prop']['alloc'], w0):.0f} %. "
                            f"Plant man nach Tagen ohne Störungslage, liegt die Verspätung {loss:+.1f} % gegenüber dem Optimum, das sie kennt."))
    opt = optimism_pct(run)
    if opt >= 5.0:
        out.append(("warning", f"Selbsttäuschung: Die {settings['data']} Planungstage versprechen {run['plan_objective']:.2f} min, frische Tage zeigen {r['saa']['delay']:.2f} min ({opt:.0f} % schlechter). Mit wenig Daten passt sich das Optimum dem Zufall dieser Tage an."))
    return out
