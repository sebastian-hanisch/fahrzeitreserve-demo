"""Das Optimierungsprogramm (SAA-LP) gegen eine Vollaufzählung aller ganzzahligen Reserven auf kleinen Instanzen (unabhängiger Rechenweg: nur die naive Fortpflanzung)."""
import itertools

import numpy as np
import pytest

import rsv_constants as C
import rsv_model as M
import rsv_saa as S
from test_model import naive


def compositions(total, parts):
    for c in itertools.combinations(range(total + parts - 1), parts - 1):
        prev = -1
        out = []
        for x in c + (total + parts - 1,):
            out.append(x - prev - 1)
            prev = x
        yield tuple(out)


def brute(E, g, B, w, lo):
    best = None
    wn = w / w.sum()
    for a in compositions(B, E.shape[2]):
        if any(x < l for x, l in zip(a, lo)):
            continue
        d = float((naive(np.array(a, float), E, g) * wn).sum(axis=2).mean())
        if best is None or d < best[0] - 1e-12:
            best = (d, a)
    return best


def small(seed, S_=6, Mn=2, n=4):
    rng = np.random.default_rng(seed)                                    # nur Testdaten, kein Bestandteil der Demo
    E = np.where(rng.random((S_, Mn, n)) < 0.5, rng.integers(1, 6, (S_, Mn, n)), 0).astype(float)
    return E, rng


def test_compositions_helper():
    assert sorted(compositions(2, 2)) == [(0, 2), (1, 1), (2, 0)] and len(list(compositions(5, 4))) == 56


def test_lp_equals_brute_force_on_random_small_instances():
    for seed in range(40):
        E, rng = small(seed)
        g = rng.integers(0, 3, 4).astype(float)
        B = 5 * int(rng.integers(1, 5))                                  # Zehntelminuten
        w = np.ones(4)
        lo = np.zeros(4)
        a, obj = S.optimal_reserve(E, g, B, w, lo)
        best = brute(E, g, B, w, lo)
        assert a.sum() == B and (a == np.round(a)).all()
        assert obj == pytest.approx(best[0], abs=1e-7), (seed, a, best)
        assert float((naive(a, E, g) * (w / w.sum())).sum(axis=2).mean()) == pytest.approx(obj, abs=1e-7)       # der LP-Wert ist die simulierte Verspätung


def test_lp_with_floor_and_weights_equals_brute_force():
    for seed in range(25):
        E, rng = small(100 + seed)
        g = rng.integers(0, 3, 4).astype(float)
        B = 20
        lo = np.array([5, 0, 5, 0], float)
        for name in ("ende", "last"):
            w = M.score_weights(name, 4)
            a, obj = S.optimal_reserve(E, g, B, w, lo)
            best = brute(E, g, B, w, lo)
            assert (a >= lo).all() and a.sum() == B and obj == pytest.approx(best[0], abs=1e-7), (seed, name)


def test_a_single_train_without_following_train_needs_no_spielraum_rows():
    E = np.array([[[4.0, 0.0, 0.0]], [[0.0, 3.0, 0.0]]])
    a, obj = S.optimal_reserve(E, np.zeros(3), 20, np.ones(3), np.zeros(3))
    best = brute(E, np.zeros(3), 20, np.ones(3), np.zeros(3))
    assert obj == pytest.approx(best[0]) and a.sum() == 20


def test_only_the_final_arrival_counts_puts_all_reserve_at_the_end():
    """Zählt nur die Endankunft, ist jede Verteilung mit gleichem Anteil nach dem letzten Störungsort gleich gut; mit einer einzigen Störung ganz am Ende gehört die Reserve ans Ende."""
    E = np.zeros((3, 1, 4))
    E[:, 0, 3] = 3.0
    a, obj = S.optimal_reserve(E, np.zeros(4), 30, M.score_weights("ende", 4), np.zeros(4))
    assert a.tolist() == [0, 0, 0, 30] and obj == pytest.approx(0.0)


def test_planning_on_a_single_scenario_overfits_to_that_scenario():
    E = np.zeros((1, 1, 5))
    E[0, 0, 1] = 4.0
    a, obj = S.optimal_reserve(E, np.zeros(5), 40, np.ones(5), np.zeros(5))
    assert a[1] == 40 and obj == pytest.approx(0.0)


def test_optimum_beats_the_rules_on_its_own_planning_scenarios():
    for seed in range(8):
        cfg = M.make_config(seed)
        B = M.budget_units(cfg, 5)
        g = M.gap_vector(cfg, 2)
        w = np.ones(cfg["n"])
        plan = M.disturbances(cfg, 80, 3, "aus", 500 + seed)
        a, obj = S.optimal_reserve(plan, g, B, w, np.zeros(cfg["n"]))
        for name in ("prop", "risk"):
            assert obj <= M.evaluate(M.method_allocation(name, cfg, B, 0), plan, g, w)["delay"] + 1e-9


def test_the_lp_vertex_is_integral_on_standard_instances():
    for seed in range(6):
        cfg = M.make_config(seed)
        B = M.budget_units(cfg, 5)
        a, _ = S.optimal_reserve(M.disturbances(cfg, 60, 5, "aus", 9 + seed), M.gap_vector(cfg, 2), B, np.ones(cfg["n"]), np.zeros(cfg["n"]))
        assert (a == np.round(a)).all() and a.sum() == B


def test_milp_fallback_runs_when_the_lp_vertex_is_fractional(monkeypatch):
    E, rng = small(3)
    g = np.zeros(4)
    real = S.linprog

    def fractional(*args, **kwargs):
        res = real(*args, **kwargs)
        res.x = res.x.copy()
        res.x[:4] = [0.5, 0.5, 0.5, 0.5]                                  # künstlich gebrochen, Summe 2
        return res
    monkeypatch.setattr(S, "linprog", fractional)
    a, obj = S.optimal_reserve(E, g, 2, np.ones(4), np.zeros(4))
    best = brute(E, g, 2, np.ones(4), np.zeros(4))
    assert a.sum() == 2 and (a == np.round(a)).all() and obj == pytest.approx(best[0], abs=1e-7)


def test_a_failing_lp_raises(monkeypatch):
    class Bad:
        status = 2
        message = "infeasible"
    monkeypatch.setattr(S, "linprog", lambda *a, **k: Bad())
    with pytest.raises(RuntimeError):
        S.optimal_reserve(np.zeros((1, 1, 2)), np.zeros(2), 1, np.ones(2), np.zeros(2))


def test_scenario_weights_are_normalised():
    cfg = M.make_config(2)
    E = M.disturbances(cfg, 30, 2, "aus", 4)
    g = M.gap_vector(cfg, 2)
    B = 40
    a1, o1 = S.optimal_reserve(E, g, B, np.ones(cfg["n"]), np.zeros(cfg["n"]))
    a2, o2 = S.optimal_reserve(E, g, B, 7 * np.ones(cfg["n"]), np.zeros(cfg["n"]))
    assert o1 == pytest.approx(o2) and C.N_SECTIONS == cfg["n"]
