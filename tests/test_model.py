"""Strecke, Störungen, Fortpflanzung und Faustregeln von Hand gerechnet; die Rekursion zusätzlich gegen eine naive Dreifachschleife."""
import numpy as np
import pytest

import rsv_constants as C
import rsv_model as M
from rsv_rng import Stream


def cfg3():
    return {"n": 3, "r": np.array([10, 20, 30]), "p": np.array([50, 50, 50]), "mu": np.array([30, 30, 30]), "bott": (1,), "w0": 0, "seed": 0}


def test_budget_units_rounds_half_up_with_a_floor_of_one():
    mk = lambda total: {"r": np.array([total])}
    assert M.budget_units(mk(120), 5) == 60 and M.budget_units(mk(120), 3) == 36 and M.budget_units(mk(120), 1) == 12 and M.budget_units(mk(120), 10) == 120      # Zehntelminuten
    assert M.budget_units(mk(115), 5) == 58 and M.budget_units(mk(110), 5) == 55 and M.budget_units(mk(90), 5) == 45 and M.budget_units(mk(30), 1) == 3 and M.budget_units(mk(1), 1) == 1


def test_score_weights():
    assert list(M.score_weights("alle", 4)) == [1, 1, 1, 1] and list(M.score_weights("ende", 4)) == [0, 0, 0, 1]
    assert list(M.score_weights("last", 12)) == [1, 2, 3, 4, 5, 6, 6, 5, 4, 3, 2, 1] and list(M.score_weights("last", 5)) == [1, 2, 3, 2, 1]
    with pytest.raises(ValueError):
        M.score_weights("alles", 3)


def test_gap_vector_has_zero_spielraum_at_the_bottlenecks():
    assert list(M.gap_vector(cfg3(), 2)) == [2, 0, 2]


def test_config_is_integer_frozen_and_valid():
    a, b = M.make_config(1), M.make_config(1)
    assert all((a[k] == b[k]).all() if isinstance(a[k], np.ndarray) else a[k] == b[k] for k in a) and M.make_config(2)["r"].tolist() != a["r"].tolist()
    assert a["r"].tolist() == [10, 10, 5, 7, 9, 6, 8, 15, 15, 9, 11, 8] and a["p"].tolist() == [93, 106, 103, 41, 71, 70, 113, 59, 44, 64, 83, 44]
    assert a["mu"].tolist() == [36, 27, 27, 29, 24, 22, 29, 40, 36, 24, 18, 23] and a["bott"] == (2, 8) and a["w0"] == 2
    for seed in range(200):
        c = M.make_config(seed)
        assert c["r"].min() >= C.RUN_MIN and c["r"].max() <= C.RUN_MAX and c["p"].min() >= C.P_MIN and c["p"].max() < C.P_MIN + C.P_SPAN
        assert c["mu"].min() >= C.MU_TENTHS_MIN and c["mu"].max() < C.MU_TENTHS_MIN + C.MU_TENTHS_SPAN
        assert len(set(c["bott"])) == C.N_BOTTLENECKS and 0 not in c["bott"] and 0 <= c["w0"] <= c["n"] - C.SHOCK_WINDOW


def test_bottleneck_and_window_positions_cover_the_strecke():
    bott = {k for s in range(300) for k in M.make_config(s)["bott"]}
    w0 = {M.make_config(s)["w0"] for s in range(300)}
    assert bott == set(range(1, 12)) and w0 == set(range(0, 9))


def test_mag_table_is_the_geometric_distribution():
    assert M.mag_table(20)[:4] == [500000, 750000, 875000, 937500]
    assert M.mag_table(40)[:3] == [250000, 437500, 578125] and len(M.mag_table(30)) == C.CAP - 1
    u = Stream(5).below(1_000_000, (400000,))
    mag = 1 + np.searchsorted(np.array(M.mag_table(30)), u, side="right")
    assert abs(mag.mean() - 3.0) < 0.03 and mag.min() == 1 and mag.max() <= C.CAP


def test_magnitude_boundaries_belong_to_the_next_height():
    t = M.mag_table(20)                                                              # 500000, 750000, 875000, ...
    assert M.magnitude(np.array([0, t[0] - 1, t[0], t[1] - 1, t[1], 999999]), 20).tolist() == [1, 1, 2, 2, 3, M.magnitude(np.array([999999]), 20)[0]]
    assert M.magnitude(np.array([999999]), 20)[0] <= C.CAP


def test_disturbances_have_the_right_shape_and_rates():
    cfg = M.make_config(3)
    E = M.disturbances(cfg, 4000, 3, "aus", 11)
    assert E.shape == (4000, 3, 12) and E.min() == 0 and E.max() <= C.CAP
    rate = (E > 0).mean(axis=(0, 1))
    assert np.allclose(rate, cfg["p"] / 1000, atol=0.012)
    mean_mag = E.sum(axis=(0, 1)) / np.maximum((E > 0).sum(axis=(0, 1)), 1)
    assert np.allclose(mean_mag, cfg["mu"] / 10, atol=0.4)


def test_the_same_days_are_comparable_with_and_without_a_shock():
    cfg = M.make_config(3)
    base = M.disturbances(cfg, 3000, 4, "aus", 11)
    shock = M.disturbances(cfg, 3000, 4, "haeufig", 11)
    assert (shock >= base).all()                                                  # dieselben Tage: mit Störungslage nie weniger Störungen
    diff = np.argwhere(shock != base)
    w0, w1 = cfg["w0"], cfg["w0"] + C.SHOCK_WINDOW
    assert len(diff) > 0 and diff[:, 2].min() >= w0 and diff[:, 2].max() < w1      # nur im Fenster
    bad_days = np.unique(diff[:, 0])
    rate_bad_days = len(bad_days) / 3000
    assert 0.12 < rate_bad_days < 0.32                                           # 30 % der Tage sind Störungslage, nicht jeder löst eine zusätzliche Störung aus
    assert (M.disturbances(cfg, 3000, 4, "selten", 11) <= shock).all()


def test_the_shock_hits_all_trains_of_a_bad_day_not_single_trains():
    cfg = M.make_config(3)
    base = M.disturbances(cfg, 3000, 6, "aus", 11)
    shock = M.disturbances(cfg, 3000, 6, "haeufig", 11)
    extra_trains = ((shock != base).any(axis=2)).sum(axis=1)                      # je Tag: Züge mit zusätzlicher Störung
    assert extra_trains.max() >= 2 and (extra_trains > 0).sum() > 0               # mehrere Züge am selben Tag


def test_simulate_by_hand_single_train():
    E = np.array([[[4.0, 0.0, 0.0]]])
    assert M.simulate(np.array([10, 10, 10]), E, np.zeros(3))[0, 0].tolist() == [3, 2, 1]                       # a in Zehntelminuten: 10 = 1 min
    assert M.simulate(np.array([0, 20, 0]), E, np.zeros(3))[0, 0].tolist() == [4, 2, 2]
    assert M.simulate(np.array([50, 0, 0]), E, np.zeros(3))[0, 0].tolist() == [0, 0, 0]
    assert M.simulate(np.array([5, 0, 0]), E, np.zeros(3))[0, 0].tolist() == [3.5, 3.5, 3.5]


def test_simulate_by_hand_following_train_is_pulled_along():
    E = np.array([[[4.0, 0.0, 0.0], [0.0, 0.0, 0.0]]])
    a = np.array([10, 10, 10])
    assert M.simulate(a, E, np.array([0.0, 0.0, 0.0]))[0, 1].tolist() == [3, 2, 1]        # kein Spielraum: Folgezug kopiert den Vorderzug
    assert M.simulate(a, E, np.array([2.0, 2.0, 2.0]))[0, 1].tolist() == [1, 0, 0]        # 2 min Spielraum: Rest wird vor dem nächsten Abschnitt aufgeholt
    assert M.simulate(a, E, np.array([9.0, 9.0, 9.0]))[0, 1].tolist() == [0, 0, 0]


def naive(a, E, g):
    S, Mn, n = E.shape
    out = np.zeros((S, Mn, n))
    for s in range(S):
        for j in range(Mn):
            for k in range(n):
                left = out[s, j, k - 1] if k > 0 else 0.0
                above = out[s, j - 1, k] - g[k] if j > 0 else -1e9
                out[s, j, k] = max(0.0, left + E[s, j, k] - a[k] / C.UNITS_PER_MIN, above)
    return out


def test_simulate_equals_a_naive_triple_loop_on_random_scenarios():
    cfg = M.make_config(8)
    E = M.disturbances(cfg, 60, 4, "haeufig", 5)
    g = M.gap_vector(cfg, 2)
    for a in (np.zeros(12), (np.arange(12) % 3) * 10, np.full(12, 7.0)):
        assert np.array_equal(M.simulate(a, E, g), naive(a, E, g))


def test_evaluate_by_hand():
    E = np.array([[[4.0, 0.0, 0.0]]])
    ev = M.evaluate(np.array([10, 10, 10]), E, np.zeros(3), np.ones(3))
    assert ev["delay"] == pytest.approx(2.0) and ev["punct"] == 1.0 and ev["profile"].tolist() == [3, 2, 1]                   # (3 + 2 + 1) / 3, alle <= 3 min
    ev = M.evaluate(np.array([0, 0, 0]), E, np.zeros(3), np.ones(3))
    assert ev["delay"] == pytest.approx(4.0) and ev["punct"] == 0.0
    assert M.evaluate(np.array([10, 10, 10]), E, np.zeros(3), M.score_weights("ende", 3))["delay"] == pytest.approx(1.0)          # nur die Endankunft zählt
    assert M.evaluate(np.array([10, 10, 10]), E, np.zeros(3), np.array([1.0, 2.0, 1.0]))["delay"] == pytest.approx((3 + 4 + 1) / 4)


def test_round_largest_remainder_keeps_the_sum_and_breaks_ties_by_index():
    assert M.round_largest_remainder(np.array([1.5, 2.25, 2.25]), 6).tolist() == [2, 2, 2]
    assert M.round_largest_remainder(np.array([0.5, 0.5]), 1).tolist() == [1, 0]
    assert M.round_largest_remainder(np.array([2.0, 3.0]), 5).tolist() == [2, 3]
    assert M.round_largest_remainder(np.array([0.5, 0.75, 0.75, 1.0]), 3).tolist() == [0, 1, 1, 1]                 # Reste 0.5, 0.75, 0.75, 0: die beiden 0.75 gewinnen


def test_floor_vector_is_the_share_of_the_proportional_allocation_rounded_down():
    cfg = {"r": np.array([10, 20, 30])}
    assert M.floor_vector(cfg, 60, 50).tolist() == [5, 10, 15] and M.floor_vector(cfg, 60, 0).tolist() == [0, 0, 0] and M.floor_vector(cfg, 60, 100).tolist() == [10, 20, 30]
    assert M.floor_vector(cfg, 7, 50).tolist() == [0, 1, 1]                                                       # 7 Einheiten: Anteile 1.17, 2.33, 3.5; die Hälfte abgerundet


def test_allocate_distributes_above_the_floor_by_weight():
    assert M.allocate(np.array([1, 1, 2]), 8, np.array([1, 1, 1])).tolist() == [2, 2, 4]
    assert M.allocate(np.array([5, 1]), 6, np.array([0, 0])).tolist() == [5, 1]


def test_method_allocations_by_hand():
    cfg = cfg3()
    assert M.method_allocation("prop", cfg, 60, 0).tolist() == [10, 20, 30]                   # proportional zur Fahrzeit 10 : 20 : 30
    cfg2 = {**cfg, "p": np.array([100, 50, 50]), "mu": np.array([40, 20, 20])}
    assert M.method_allocation("risk", cfg2, 60, 0).tolist() == [40, 10, 10]                  # p * mu = 4000 : 1000 : 1000
    assert M.method_allocation("prop", cfg, 60, 100).tolist() == [10, 20, 30] and M.method_allocation("risk", cfg2, 60, 100).sum() == 60
    assert (M.method_allocation("risk", cfg2, 60, 75) >= M.floor_vector(cfg2, 60, 75)).all() and M.method_allocation("risk", cfg2, 60, 75).sum() == 60
    with pytest.raises(ValueError):
        M.method_allocation("zufall", cfg, 6, 0)


def test_every_allocation_has_the_budget_as_sum_in_whole_units():
    for seed in range(40):
        cfg = M.make_config(seed)
        for pct in (1, 5, 10):
            B = M.budget_units(cfg, pct)
            for share in C.SHARE_OPTIONS:
                for name in ("prop", "risk"):
                    a = M.method_allocation(name, cfg, B, share)
                    assert a.sum() == B and (a == np.round(a)).all() and (a >= M.floor_vector(cfg, B, share)).all()
