"""Strecke, Störungen, Verspätungsfortpflanzung (max-plus) und die beiden Faustregeln der Fahrzeitreserve-Demo.

Eine Strecke mit n Abschnitten (Fahrt plus Halt); M Züge fahren hintereinander. Jeder Abschnitt k hat eine planmäßige Reserve a_k (in Zehntelminuten, Summe = Budget B), dieselbe für alle Züge.
Verspätung am Ende von Abschnitt k des Zuges j:
    A[j,k] = max(0, A[j,k-1] + e[j,k] - a[k], A[j-1,k] - g[k])
e = Störung im Abschnitt, g[k] = Zugfolge-Spielraum am Abschnittsende (geplanter Abstand minus Mindestzugfolge): ist der Vorderzug um mehr als g[k] verspätet, wird der Folgezug mitgezogen.
Alles Ganzzahlige (Störungen in Minuten, Wahrscheinlichkeiten in Promille) kommt aus SplitMix64 (`rsv_rng.py`).
"""
from __future__ import annotations

import numpy as np

import rsv_constants as C
from rsv_rng import SplitMix64, Stream


# ------------------------------------------------------------------ Strecke
def make_config(seed: int, n: int = C.N_SECTIONS) -> dict:
    """Zufällige Strecke: Fahrzeit, Störungswahrscheinlichkeit (Promille) und mittlere Störungshöhe (Zehntelminuten) je Abschnitt, zwei Engpässe, Fenster der Störungslage."""
    rng = SplitMix64(seed)
    r = [C.RUN_MIN + rng.below(C.RUN_MAX - C.RUN_MIN + 1) for _ in range(n)]
    p = [C.P_MIN + rng.below(C.P_SPAN) for _ in range(n)]
    mu = [C.MU_TENTHS_MIN + rng.below(C.MU_TENTHS_SPAN) for _ in range(n)]
    pool = list(range(1, n))                                   # der erste Abschnitt ist nie ein Engpass
    bott = []
    for _ in range(C.N_BOTTLENECKS):
        bott.append(pool.pop(rng.below(len(pool))))
    w0 = rng.below(n - C.SHOCK_WINDOW + 1)
    return {"seed": seed, "n": n, "r": np.array(r, dtype=np.int64), "p": np.array(p, dtype=np.int64), "mu": np.array(mu, dtype=np.int64), "bott": tuple(sorted(bott)), "w0": w0}


def gap_vector(cfg: dict, gap: int) -> np.ndarray:
    """Zugfolge-Spielraum je Abschnittsende: an den Engpässen 0, sonst `gap` Minuten."""
    g = np.full(cfg["n"], float(gap))
    for k in cfg["bott"]:
        g[k] = 0.0
    return g


def budget_units(cfg: dict, pct: int) -> int:
    """Reservebudget in Zehntelminuten: pct Prozent der planmäßigen Fahrzeit, kaufmännisch gerundet, mindestens 1."""
    return max(1, (int(cfg["r"].sum()) * pct * C.UNITS_PER_MIN + 50) // 100)


def score_weights(name: str, n: int) -> np.ndarray:
    """Wertung: wo zählt die Verspätung? alle Halte gleich, nur die Endankunft, oder Fahrgastlast (Gewicht min(k+1, n-k), Mitte schwerer)."""
    if name == "alle":
        return np.ones(n)
    if name == "ende":
        w = np.zeros(n)
        w[-1] = 1.0
        return w
    if name == "last":
        return np.array([min(k + 1, n - k) for k in range(n)], dtype=float)
    raise ValueError(name)


# ------------------------------------------------------------------ Störungen
def mag_table(mu_tenths: int) -> list:
    """Obere Grenzen (in Millionstel) der geometrisch verteilten Störungshöhe 1, 2, 3 ... mit Mittel mu = mu_tenths / 10 min; nur Multiplikation und Subtraktion in IEEE-Arithmetik."""
    q = 10.0 / mu_tenths
    surv = 1.0
    out = []
    for _ in range(C.CAP - 1):
        surv = surv * (1.0 - q)
        out.append(int((1.0 - surv) * 1_000_000))
    return out


def magnitude(u, mu_tenths: int):
    """Störungshöhe (ganze Minuten, mindestens 1) zu Gleichverteilten u in 0..999999: Höhe 1 bei u < T[0], Höhe 2 bei T[0] <= u < T[1] usw. (T = `mag_table`)."""
    return 1 + np.searchsorted(np.array(mag_table(mu_tenths)), u, side="right")


def disturbances(cfg: dict, S: int, M: int, corr: str, seed: int) -> np.ndarray:
    """E[s, j, k]: Störung (ganze Minuten, 0 = keine) von Szenario (Tag) s, Zug j, Abschnitt k. Eine Störungslage (`corr` selten/häufig) hebt an einem Teil der Tage die Wahrscheinlichkeit
    in einem Fenster benachbarter Abschnitte für ALLE Züge dieses Tages. Alle Zufallszahlen werden unabhängig von `corr` gezogen: dieselben Tage ohne und mit Störungslage sind vergleichbar."""
    n = cfg["n"]
    st = Stream(seed)
    day = st.below(1000, (S,))
    u_occ = st.below(1000, (S, M, n))
    u_mag = st.below(1_000_000, (S, M, n))
    bad = day < C.CORR_PERMILLE[corr]
    p = np.broadcast_to(cfg["p"], (S, 1, n)).copy()
    w0, w1 = cfg["w0"], cfg["w0"] + C.SHOCK_WINDOW
    p[bad, :, w0:w1] = np.minimum(p[bad, :, w0:w1] * C.SHOCK_FACTOR, 600)
    occ = u_occ < p
    mag = np.empty((S, M, n), dtype=np.int64)
    for k in range(n):
        mag[:, :, k] = magnitude(u_mag[:, :, k], int(cfg["mu"][k]))
    return np.where(occ, mag, 0).astype(float)


# ------------------------------------------------------------------ Verspätungsfortpflanzung
def simulate(a: np.ndarray, E: np.ndarray, g: np.ndarray) -> np.ndarray:
    """Max-plus-Rekursion, vektorisiert über die Szenarien; `a` in Zehntelminuten, E und g in Minuten. Rückgabe A[s, j, k] (Verspätung am Ende des Abschnitts k, Minuten)."""
    a = np.asarray(a, dtype=float) / C.UNITS_PER_MIN
    S, M, n = E.shape
    A = np.zeros((S, M, n))
    for j in range(M):
        prev = np.zeros(S)
        for k in range(n):
            v = prev + E[:, j, k] - a[k]
            if j > 0:
                v = np.maximum(v, A[:, j - 1, k] - g[k])
            v = np.maximum(v, 0.0)
            A[:, j, k] = v
            prev = v
    return A


def evaluate(a: np.ndarray, E: np.ndarray, g: np.ndarray, w: np.ndarray) -> dict:
    """Mittlere gewichtete Verspätung, Pünktlichkeit (Anteil der gewichteten Ankünfte mit höchstens 3 min) und das Verspätungsprofil entlang der Strecke."""
    A = simulate(a, E, g)
    wn = w / w.sum()
    return {"delay": float((A * wn).sum(axis=2).mean()), "punct": float(((A <= C.PUNKT + 1e-9) * wn).sum(axis=2).mean()), "profile": A.mean(axis=(0, 1))}


# ------------------------------------------------------------------ Faustregeln
def round_largest_remainder(a: np.ndarray, B: int) -> np.ndarray:
    """Rundet eine Verteilung mit Summe B auf ganze Einheiten, Summe bleibt B (größter Rest zuerst, bei Gleichstand der kleinere Index)."""
    fl = np.floor(a + 1e-12)
    need = int(round(B - fl.sum()))
    order = np.argsort(-(a - fl), kind="stable")
    out = fl.copy()
    for k in order[:max(need, 0)]:
        out[k] += 1
    return out


def floor_vector(cfg: dict, B: int, share: int) -> np.ndarray:
    """Mindestreserve je Abschnitt in Zehntelminuten: `share` Prozent des proportionalen Anteils B * r_k / sum(r), abgerundet."""
    r = cfg["r"]
    return np.floor(share / 100.0 * B * r / r.sum() + 1e-9)


def allocate(weights: np.ndarray, B: int, lo: np.ndarray) -> np.ndarray:
    """Verteilt B proportional zu `weights` oberhalb der Mindestreserve `lo` und rundet auf Zehntelminuten."""
    w = np.asarray(weights, dtype=float)
    free = B - lo.sum()
    return round_largest_remainder(lo + free * w / w.sum(), B)


def method_allocation(name: str, cfg: dict, B: int, share: int) -> np.ndarray:
    """Praxisregel `prop` (proportional zur Fahrzeit) und `risk` (proportional zum erwarteten Störungsbeitrag p * mu)."""
    lo = floor_vector(cfg, B, share)
    if name == "prop":
        return allocate(cfg["r"], B, lo)
    if name == "risk":
        return allocate(cfg["p"] * cfg["mu"], B, lo)
    raise ValueError(name)
