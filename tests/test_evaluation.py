"""Live-Rechnung und Meldungen: eingefrorene Werte für den Standardfall, Eigenschaften jedes Laufs, Meldungen an ihren Schwellen mit künstlichen Zahlen."""
import numpy as np
import pytest

import rsv_constants as C
import rsv_evaluation as E
import rsv_model as M

STD = {"budget": 5, "trains": 5, "gap": 2, "score": "alle", "share": 0, "corr": "aus", "data": 200, "seed": 500}


def fake(prop=2.0, saa=1.6, risk=1.8, plan=1.6, blind=None, w0=2, saa_alloc=None):
    saa_alloc = saa_alloc or [0, 0, 10, 30, 0, 0, 0, 10, 20, 0, 0, 0]
    r = {"none": {"alloc": [0] * 12, "delay": 3.0, "punct": 0.7, "profile": [0.0] * 12}, "prop": {"alloc": [6] * 12, "delay": prop, "punct": 0.8, "profile": [0.0] * 12},
         "risk": {"alloc": [6] * 12, "delay": risk, "punct": 0.8, "profile": [0.0] * 12}, "saa": {"alloc": saa_alloc, "delay": saa, "punct": 0.85, "profile": [0.0] * 12}}
    if blind is not None:
        r["saa_blind"] = {"alloc": [5] * 12, "delay": blind, "punct": 0.8, "profile": [0.0] * 12}
    return {"cfg": {"n": 12, "bott": (3, 11), "w0": w0}, "corr": "aus", "B": 72, "results": r, "plan_objective": plan, "seconds": 0.0}


def test_standard_run_is_frozen():
    run = E.run_live(STD)
    r = run["results"]
    assert run["B"] == 70 and run["cfg"]["bott"] == (3, 11) and run["cfg"]["w0"] == 5
    assert r["saa"]["alloc"] == [0, 0, 10, 30, 0, 0, 0, 10, 20, 0, 0, 0] and r["none"]["alloc"] == [0] * 12
    assert r["prop"]["alloc"] == [8, 2, 5, 5, 7, 8, 7, 4, 8, 6, 4, 6] and r["risk"]["alloc"] == [5, 4, 8, 7, 2, 6, 6, 9, 11, 4, 4, 4]
    assert r["none"]["delay"] == pytest.approx(2.724, abs=5e-4) and r["prop"]["delay"] == pytest.approx(1.3319, abs=5e-4) and r["saa"]["delay"] == pytest.approx(1.1494, abs=5e-4)
    assert r["saa"]["punct"] == pytest.approx(0.8814, abs=5e-4) and run["plan_objective"] == pytest.approx(1.3835, abs=5e-4)


def test_every_allocation_sums_to_the_budget_and_respects_the_floor():
    for share in C.SHARE_OPTIONS:
        run = E.run_live({**STD, "share": share, "data": 50})
        lo = M.floor_vector(run["cfg"], run["B"], share)
        for key in ("prop", "risk", "saa"):
            a = np.array(run["results"][key]["alloc"])
            assert a.sum() == run["B"] and (a >= lo).all(), (share, key)


def test_blind_optimum_exists_only_with_a_shock():
    assert "saa_blind" not in E.run_live({**STD, "data": 50})["results"]
    run = E.run_live({**STD, "corr": "haeufig", "data": 50})
    assert "saa_blind" in run["results"] and run["corr"] == "haeufig" and run["results"]["saa_blind"]["alloc"] != run["results"]["saa"]["alloc"]


def test_the_optimum_wins_when_only_the_final_arrival_counts():
    run = E.run_live({**STD, "score": "ende"})
    r = run["results"]
    assert sum(r["saa"]["alloc"][-2:]) == run["B"] and r["saa"]["delay"] < 0.6 * r["prop"]["delay"]


def test_every_setting_changes_the_run():
    ref = E.run_live({**STD, "data": 50})
    snap = {k: (tuple(v["alloc"]), round(v["delay"], 6)) for k, v in ref["results"].items()}
    for change in ({"budget": 8}, {"trains": 3}, {"gap": 4}, {"score": "last"}, {"share": 50}, {"corr": "haeufig"}, {"data": 100}, {"seed": 501}):
        other = E.run_live({**STD, "data": 50, **change})
        assert {k: (tuple(v["alloc"]), round(v["delay"], 6)) for k, v in other["results"].items() if k in snap} != snap, change


def test_a_different_planning_set_changes_only_the_optimum_and_the_plan_value():
    a, b = E.run_live({**STD, "data": 50}, rep=0), E.run_live({**STD, "data": 50}, rep=1)
    assert a["results"]["prop"]["delay"] == b["results"]["prop"]["delay"] and a["results"]["saa"]["alloc"] != b["results"]["saa"]["alloc"] and a["plan_objective"] != b["plan_objective"]


def test_train_argument_overrides_the_planning_days():
    a = E.run_live({**STD, "data": 400}, train=25)
    b = E.run_live({**STD, "data": 25})
    assert a["results"]["saa"]["alloc"] == b["results"]["saa"]["alloc"] and a["plan_objective"] == b["plan_objective"]


def test_gain_and_over_use_the_stated_base():
    run = fake(prop=2.0, saa=1.6)
    assert E.gain_pct(run) == pytest.approx(20.0) and E.over_pct(run) == pytest.approx(25.0)                  # 20 % weniger gegen 25 % mehr: verschiedene Basis
    assert E.gain_pct(run, "risk", "prop") == pytest.approx(10.0) and E.over_pct(run, "none", "prop") == pytest.approx(50.0)


def test_centroid_window_and_optimism():
    assert E.centroid_pct([0, 0, 0, 4]) == 100.0 and E.centroid_pct([4, 0, 0, 0]) == 0.0 and E.centroid_pct([1, 1, 1, 1]) == pytest.approx(50.0) and E.centroid_pct([0, 0]) != E.centroid_pct([0, 0])
    assert E.window_pct([1, 1, 1, 1, 4, 0], 0) == pytest.approx(50.0) and E.window_pct([1, 1, 1, 1, 4, 0], 2) == pytest.approx(75.0) and E.window_pct([0, 0], 0) != E.window_pct([0, 0], 0)
    assert E.optimism_pct(fake(saa=4.0, plan=3.8)) == pytest.approx(5.0) and E.optimism_pct(fake(saa=4.0, plan=4.2)) == pytest.approx(-5.0)


def texts(run, **over):
    return E.messages(run, {**STD, **over})


def test_gain_message_thresholds():
    state, text = texts(fake(prop=2.0, saa=1.5))[0]                                       # 25 %: success
    assert state == "success" and "25 %" in text and "4 von 12 Abschnitten" in text
    assert texts(fake(prop=2.0, saa=1.79))[0][0] == "success" and texts(fake(prop=2.0, saa=1.81))[0][0] == "info"            # Schwelle 10 % (10,5 % und 9,5 %)
    state, text = texts(fake(prop=2.0, saa=1.99))[0]                                      # 0,5 %: gleichauf
    assert state == "info" and "gleichauf" in text
    assert texts(fake(prop=2.0, saa=1.97))[0][1].startswith("Das Optimum senkt") and texts(fake(prop=2.0, saa=1.99))[0][1].startswith("Praxisregel und Optimum liegen")   # Schwelle 1 %


def test_gain_message_names_the_centroids():
    text = texts(fake(saa_alloc=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 72]))[0][1]
    assert "Schwerpunkt bei 100 %" in text and "Praxisregel 50 %" in text


def test_score_messages():
    assert any("Es zählt nur die Endankunft" in t for _, t in texts(fake(saa_alloc=[0] * 10 + [12, 60]), score="ende")) and all("Endankunft" not in t for _, t in texts(fake()))
    assert any("100 % der Reserve in die letzten beiden Abschnitte" in t for _, t in texts(fake(saa_alloc=[0] * 10 + [12, 60]), score="ende"))
    assert any("Fahrgastlast" in t for _, t in texts(fake(), score="last"))


def test_shock_message_reports_the_window_and_the_blind_loss():
    out = texts(fake(blind=1.8, saa=1.6, w0=2, saa_alloc=[0, 0, 10, 30, 0, 0, 0, 10, 20, 0, 0, 0]), corr="haeufig")
    text = next(t for _, t in out if t.startswith("Störungslagen"))
    assert "Abschnitte 3 bis 6" in text and "57 %" in text and "33 %" in text and "+12.5 %" in text           # Fenster 3..6: 10+30 von 70, Praxisregel gleichmäßig 4/12


def test_optimism_message_appears_from_five_percent():
    run = fake(saa=4.0, prop=5.0, plan=3.8)                                                 # 5,0 %: Warnung
    assert any(s == "warning" and "Selbsttäuschung" in t and "200 Planungstage" in t for s, t in texts(run))
    assert not any(s == "warning" for s, _ in texts(fake(saa=4.0, prop=5.0, plan=3.81)))      # 4,75 %: keine
    assert not any(s == "warning" for s, _ in texts(fake(saa=4.0, prop=5.0, plan=4.4)))       # negativ: Planung war pessimistisch
