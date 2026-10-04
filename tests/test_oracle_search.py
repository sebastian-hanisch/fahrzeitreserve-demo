"""Zweiter unabhängiger Rechenweg für das Optimum: eine Lokalsuche über ganzzahlige Reserven (Einheit verschieben) darf das LP auf den Planungstagen nie unterbieten, und das LP ist ein lokales Optimum."""
import numpy as np
import pytest

import rsv_model as M
import rsv_saa as S


def local_search(a, E, g, w, lo):
    best = M.evaluate(a, E, g, w)["delay"]
    improved = True
    while improved:
        improved = False
        for i in range(len(a)):
            for j in range(len(a)):
                if i != j and a[i] > lo[i]:
                    b = a.copy()
                    b[i] -= 1
                    b[j] += 1
                    d = M.evaluate(b, E, g, w)["delay"]
                    if d < best - 1e-12:
                        a, best, improved = b, d, True
    return a, best


@pytest.mark.parametrize("seed,share,score", [(3, 0, "alle"), (4, 50, "alle"), (5, 0, "last"), (6, 0, "ende")])
def test_the_lp_is_not_beaten_by_a_local_search_and_is_locally_optimal(seed, share, score):
    cfg = M.make_config(seed)
    B = M.budget_units(cfg, 3)
    g = M.gap_vector(cfg, 2)
    w = M.score_weights(score, cfg["n"])
    lo = M.floor_vector(cfg, B, share)
    E = M.disturbances(cfg, 40, 3, "aus", 91 + seed)
    a, obj = S.optimal_reserve(E, g, B, w, lo)
    start = M.method_allocation("prop", cfg, B, share).astype(float)
    _, searched = local_search(start, E, g, w, lo)
    assert obj <= searched + 1e-9
    again, value = local_search(a.astype(float), E, g, w, lo)
    assert value == pytest.approx(obj, abs=1e-9) and np.array_equal(again, a)
