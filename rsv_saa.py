"""Optimum nach Sample-Average-Approximation: lineares Programm über S Planungsszenarien (beobachtete Tage).

Variablen: Reserve a_k je Abschnitt und Verspätung A[s,j,k] je Szenario, Zug und Abschnitt. Die max-Beziehungen der Rekursion werden als Ungleichungen A >= ... geschrieben (Epigraph);
weil die Zielfunktion A nur mit nichtnegativem Gewicht enthält, ist das LP gleich dem Minimum über alle Reserven. Das Problem ist konvex (Maximum affiner Funktionen).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import coo_matrix

import rsv_constants as C


def _build(E: np.ndarray, g: np.ndarray, w: np.ndarray):
    S, M, n = E.shape
    nA = S * M * n
    idx = np.arange(nA).reshape(S, M, n)
    flat = idx.reshape(-1)
    rows, cols, vals, rhs = [], [], [], []
    # (1) A[s,j,k] >= A[s,j,k-1] + e - a_k   <=>   A[k-1] - A[k] - a_k <= -e   (A[-1] = 0)
    r1 = np.arange(nA)
    rows.append(r1); cols.append(n + flat); vals.append(-np.ones(nA)); rhs.append(-E.reshape(-1))
    rows.append(r1); cols.append(np.broadcast_to(np.arange(n), (S, M, n)).reshape(-1)); vals.append(-np.ones(nA))
    has_prev = np.ones((S, M, n), bool)
    has_prev[:, :, 0] = False
    hp = has_prev.reshape(-1)
    rows.append(r1[hp]); cols.append(n + flat[hp] - 1); vals.append(np.ones(int(hp.sum())))
    count = nA
    # (2) A[s,j,k] >= A[s,j-1,k] - g_k   <=>   A[j-1] - A[j] <= g_k
    if M > 1:
        sel = np.zeros((S, M, n), bool)
        sel[:, 1:, :] = True
        ids = np.where(sel.reshape(-1))[0]
        r2 = count + np.arange(len(ids))
        rows.append(r2); cols.append(n + ids); vals.append(-np.ones(len(ids)))
        rows.append(r2); cols.append(n + ids - n); vals.append(np.ones(len(ids)))
        rhs.append(np.broadcast_to(g, (S, M, n)).reshape(-1)[ids])
        count += len(ids)
    A_ub = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(count, n + nA)).tocsr()
    c = np.concatenate([np.zeros(n), np.broadcast_to(w / w.sum(), (S, M, n)).reshape(-1) / (S * M)])
    return c, A_ub, np.concatenate(rhs), nA


def optimal_reserve(E: np.ndarray, g: np.ndarray, B: int, w: np.ndarray, lo: np.ndarray) -> tuple:
    """Optimale Reserve (ganze Zehntelminuten, Summe B, a >= lo) für die Planungsszenarien E (Minuten). Rückgabe (a, mittlere Verspätung der Planungsszenarien in Minuten).
    Gerechnet wird in Zehntelminuten, damit die Daten ganzzahlig sind; das LP hat dann in der Regel eine ganzzahlige Ecke, sonst wird dasselbe Modell als MILP mit ganzzahliger Reserve gelöst."""
    unit = C.UNITS_PER_MIN
    n = E.shape[2]
    c, A_ub, b_ub, nA = _build(E * unit, g * unit, w)
    A_eq = coo_matrix((np.ones(n), (np.zeros(n, int), np.arange(n))), shape=(1, n + nA)).tocsr()
    lower = np.concatenate([lo, np.zeros(nA)])
    upper = np.concatenate([np.full(n, float(B)), np.full(nA, np.inf)])
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=[B], bounds=list(zip(lower, upper)), method="highs")
    if res.status != 0:
        raise RuntimeError(res.message)
    a = res.x[:n]
    if np.abs(a - np.round(a)).max() < 1e-6:
        return np.round(a), float(res.fun) / unit
    integrality = np.concatenate([np.ones(n), np.zeros(nA)])
    out = milp(c, constraints=[LinearConstraint(A_ub, -np.inf, b_ub), LinearConstraint(A_eq, B, B)], integrality=integrality, bounds=Bounds(lower, upper), options={"time_limit": 60.0})
    if out.x is None:
        raise RuntimeError("MILP ohne Lösung")
    return np.round(out.x[:n]), float(out.fun) / unit
