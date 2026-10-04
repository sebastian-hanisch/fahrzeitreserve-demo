"""Auswertung der Messreihe an einer von Hand gerechneten Mini-Ergebnisdatei (4 Strecken)."""
import json

import pytest

import rsv_constants as C
import rsv_results as R


def row(variant, seed, none, prop, risk, saa, blind=None, plan=1.0, alloc=None, w0=1, B=4):
    alloc = alloc or {"prop": [1, 1, 1, 1], "risk": [2, 1, 1, 0], "saa": [0, 2, 2, 0]}
    methods = {"none": {"alloc": [0, 0, 0, 0], "delay": none, "punct": 0.5}, "prop": {"alloc": alloc["prop"], "delay": prop, "punct": 0.6},
               "risk": {"alloc": alloc["risk"], "delay": risk, "punct": 0.7}, "saa": {"alloc": alloc["saa"], "delay": saa, "punct": 0.8}}
    if blind is not None:
        methods["saa_blind"] = {"alloc": [2, 2, 0, 0], "delay": blind, "punct": 0.75}
    return {"variant": variant, "seed": seed, "B": B, "n_zero": sum(1 for x in alloc["saa"] if x == 0), "bott": [1, 2], "w0": w0, "plan_objective": plan, "methods": methods}


RES = {"meta": {"variants": ["Standard", "Budget 1 %"]}, "rows": [
    row("Standard", 1, 4.0, 2.0, 1.8, 1.6, plan=1.2),
    row("Standard", 2, 4.0, 2.4, 2.0, 1.8, plan=1.8),
    row("Standard", 3, 3.0, 1.5, 1.5, 1.2, plan=1.0),
    row("Standard", 4, 5.0, 2.5, 2.2, 2.0, plan=1.5),
    row("Budget 1 %", 1, 4.0, 3.0, 3.0, 2.7),
]}


def test_mean_se_of_a_pair():
    m, se = R.mean_se([1, 3])
    assert m == 2 and se == pytest.approx(1.0)
    assert R.mean_se([5])[0] == 5 and R.mean_se([5])[1] != R.mean_se([5])[1]


def test_summary_by_hand():
    s = R.summary(RES, "Standard")
    assert s["n"] == 4 and s["B"] == 4
    assert s["delay_prop"] == pytest.approx((2.0 + 2.4 + 1.5 + 2.5) / 4) and s["delay_saa"] == pytest.approx((1.6 + 1.8 + 1.2 + 2.0) / 4)
    gains = [100 * (1 - 1.6 / 2.0), 100 * (1 - 1.8 / 2.4), 100 * (1 - 1.2 / 1.5), 100 * (1 - 2.0 / 2.5)]                 # 20, 25, 20, 20
    assert s["gain_saa"] == pytest.approx(sum(gains) / 4) and s["gain_saa"] == pytest.approx(21.25)
    over = [100 * (2.0 / 1.6 - 1), 100 * (2.4 / 1.8 - 1), 100 * (1.5 / 1.2 - 1), 100 * (2.5 / 2.0 - 1)]
    assert s["over_prop"] == pytest.approx(sum(over) / 4) and s["over_prop"] > s["gain_saa"]                          # Basis macht den Unterschied
    assert s["punct_prop"] == pytest.approx(60) and s["punct_saa"] == pytest.approx(80)
    assert s["zero_share"] == 0.5                                                                                     # saa [0,2,2,0]: zwei von vier Abschnitten ohne Reserve
    assert s["centroid_saa"] == pytest.approx(0.5) and s["centroid_prop"] == pytest.approx(0.5)
    opt = [100 * (1.6 - 1.2) / 1.6, 100 * (1.8 - 1.8) / 1.8, 100 * (1.2 - 1.0) / 1.2, 100 * (2.0 - 1.5) / 2.0]
    assert s["optimism"] == pytest.approx(sum(opt) / 4)
    share = (4.0 - 2.0) / (4.0 - 1.6)
    assert 0 < share < 1 and s["gain_none_share"] == pytest.approx(sum((a - b) / (a - c) for a, b, c in ((4, 2.0, 1.6), (4, 2.4, 1.8), (3, 1.5, 1.2), (5, 2.5, 2.0))) / 4)
    assert "saa_blind" not in " ".join(s)


def test_blind_variant_adds_loss_and_window_shares():
    res = {"meta": {"variants": ["Störungslagen häufig"]}, "rows": [row("Störungslagen häufig", 1, 4.0, 2.0, 1.8, 1.6, blind=1.8, w0=1), row("Störungslagen häufig", 2, 4.0, 2.0, 1.8, 1.5, blind=1.8, w0=2)]}
    s = R.summary(res, "Störungslagen häufig")
    assert s["blind_loss"] == pytest.approx((100 * (1.8 / 1.6 - 1) + 100 * (1.8 / 1.5 - 1)) / 2) and s["delay_saa_blind"] == pytest.approx(1.8)
    # Fenster = vier Abschnitte ab w0 (Abschnitte, die es nicht gibt, zählen nicht): saa [0,2,2,0]: w0=1 -> 4/4, w0=2 -> 2/4; prop [1,1,1,1]: 3/4 und 2/4; blind [2,2,0,0]: 2/4 und 0/4
    assert s["window_saa"] == pytest.approx((1.0 + 0.5) / 2) and s["window_prop"] == pytest.approx((0.75 + 0.5) / 2) and s["window_saa_blind"] == pytest.approx((0.5 + 0.0) / 2)


def test_centroid_and_window_share():
    assert R.centroid([0, 0, 0, 4]) == 1.0 and R.centroid([4, 0, 0, 0]) == 0.0 and R.centroid([1, 1, 1, 1]) == pytest.approx(0.5)
    assert R.centroid([0, 0]) != R.centroid([0, 0])                                                              # nan ohne Reserve
    assert R.window_share([1, 1, 1, 1, 4, 0], 0) == pytest.approx(4 / 8) and R.window_share([1, 1, 1, 1, 4, 0], 2) == pytest.approx(6 / 8) and R.window_share([0, 0], 0) != R.window_share([0, 0], 0)


def test_all_variants_follow_the_meta_order_and_carry_budget_and_data():
    res = {"meta": {"variants": ["Budget 1 %", "Standard"]}, "rows": [row("Standard", 1, 4.0, 2.0, 1.8, 1.6), row("Budget 1 %", 1, 4.0, 3.0, 3.0, 2.7)]}
    v = R.all_variants(res)
    assert [x["name"] for x in v] == ["Budget 1 %", "Standard"] and [x["B_pct"] for x in v] == [1, 5] and [x["data"] for x in v] == [200, 200]


def test_mean_allocation_is_the_share_of_the_budget_per_position():
    assert R.mean_allocation(RES, "Standard", "saa") == [0.0, 0.5, 0.5, 0.0] and R.mean_allocation(RES, "Standard", "prop") == [0.25, 0.25, 0.25, 0.25]


def test_variant_name_matches_the_seven_levers_but_not_the_seed():
    base = {"budget": 5, "trains": 5, "gap": 2, "score": "alle", "share": 0, "corr": "aus", "data": 200, "seed": 500}
    assert R.variant_name(base) == "Standard" and R.variant_name({**base, "seed": 7}) == "Standard"
    assert R.variant_name({**base, "budget": 3}) == "Budget 3 %" and R.variant_name({**base, "score": "ende"}) == "Wertung Endankunft" and R.variant_name({**base, "corr": "haeufig"}) == "Störungslagen häufig"
    assert R.variant_name({**base, "data": 400}) == "400 Planungsszenarien" and R.variant_name({**base, "data": 25}) == "25 Planungsszenarien" and R.variant_name({**base, "budget": 2}) is None and R.variant_name({**base, "share": 75}) == "Mindestanteil 75 %"


def test_variants_are_unique_and_inside_the_controls():
    names = [v[0] for v in C.SWEEP_VARIANTS]
    configs = [v[1:] for v in C.SWEEP_VARIANTS]
    assert len(set(names)) == len(names) == 19 and len(set(configs)) == len(configs)
    for _, b, t, g, s, sh, co, da in C.SWEEP_VARIANTS:
        assert C.BUDGET_MIN <= b <= C.BUDGET_MAX and t in C.TRAINS_OPTIONS and g in C.GAP_OPTIONS and s in C.SCORE_OPTIONS and sh in C.SHARE_OPTIONS and co in C.CORR_OPTIONS
        assert da in C.DATA_OPTIONS


def test_load_results_reads_a_file(tmp_path):
    f = tmp_path / "res.json"
    f.write_text(json.dumps(RES), encoding="utf-8")
    assert R.load_results(f)["meta"]["variants"] == ["Standard", "Budget 1 %"]
