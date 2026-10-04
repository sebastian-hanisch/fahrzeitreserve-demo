"""Jede Zahl aus dem README wird hier aus data/rsv_results.json nachgerechnet; die formatierten Texte müssen im README stehen.

40 Strecken je Variante (Seeds 100-139), Mittel ± Standardfehler über die Strecken, Bewertung an frischen Tagen.
"""
from pathlib import Path

import pytest

import rsv_constants as C
import rsv_evaluation as E
import rsv_results as R
import rsv_stories as S

README = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def res():
    return R.load_results()


@pytest.fixture(scope="module")
def v(res):
    return {x["name"]: x for x in R.all_variants(res)}


def pm(x, se, digits=1):
    return f"{x:.{digits}f} ± {se:.{digits}f} %"


def test_meta_and_counts(res):
    assert res["meta"]["seeds"] == [100, 140] and res["meta"]["variants"] == [x[0] for x in C.SWEEP_VARIANTS] and len(res["meta"]["variants"]) == 19
    for name in res["meta"]["variants"]:
        assert len(R.rows_of(res, name)) == 40
    assert "19 Varianten mit je 40 Strecken" in README and "Port 8970" in README
    assert all(r["reps"] == C.SWEEP_REPS.get(r["variant"], 1) for r in res["rows"])


def test_standard_case_in_the_readme(v):
    s = v["Standard"]
    assert f"**{pm(s['over_prop'], s['over_prop_se'])}** über dem Optimum (risikoproportional **{pm(s['over_risk'], s['over_risk_se'])}**)" in README
    assert f"um **{pm(s['gain_saa'], s['gain_saa_se'])}**" in README and f"sind es **{pm(s['over_prop'], s['over_prop_se']).replace('.', ',')}**" in README
    assert s["over_prop"] > s["gain_saa"] > 0                                                         # Basis macht den Unterschied


def test_budget_curve_in_the_readme(v):
    gains = [v[n]["gain_saa"] for n in ("Budget 1 %", "Budget 3 %", "Standard", "Budget 7 %", "Budget 10 %")]
    assert "um **" + " / ".join(f"{g:.1f}" for g in gains) + " %**" in README
    assert gains == sorted(gains)                                                                     # mehr Budget, mehr Vorsprung


def test_the_bump_in_the_readme(res, v):
    s = v["Standard"]
    assert f"**{100 * s['zero_share']:.0f} %** der Abschnitte ohne Reserve" in README and f"Schwerpunkt liegt bei **{100 * s['centroid_saa']:.0f} %** der Strecke (Praxisregel {100 * s['centroid_prop']:.0f} %)" in README
    assert "Das Optimum lässt 59 % der Abschnitte ohne Reserve" in README and round(100 * s["zero_share"]) == 59
    share = R.mean_allocation(res, "Standard", "saa")
    assert share[0] < 0.01 and sum(share[-2:]) < 0.02 and max(range(12), key=lambda k: share[k]) in (4, 6)                    # im ersten und in den letzten Abschnitten fast nichts, Gipfel in der Mitte


def test_the_scoring_in_the_readme(v):
    e, f = v["Wertung Endankunft"], v["Wertung Fahrgastlast"]
    assert f"**{pm(e['over_prop'], e['over_prop_se'])}** über dem Optimum, das seine Reserve ans Ende legt (Schwerpunkt **{100 * e['centroid_saa']:.0f} %**); bei Fahrgastlast **{pm(f['over_prop'], f['over_prop_se'])}**" in README
    assert e["over_prop"] > 40 and e["centroid_saa"] > 0.9 and f["centroid_saa"] < v["Standard"]["centroid_saa"]


def test_the_minimum_share_in_the_readme(v):
    a, b = v["Mindestanteil 50 %"], v["Mindestanteil 75 %"]
    assert f"nur noch um **{pm(a['gain_saa'], a['gain_saa_se'])}** (Mindestanteil 50 %) bzw. **{pm(b['gain_saa'], b['gain_saa_se'])}** (75 %)" in README
    assert a["zero_share"] == 0 and b["zero_share"] == 0 and b["gain_saa"] < a["gain_saa"] < v["Standard"]["gain_saa"] and "auf 7 bis 10 %" in README and 6.5 < b["gain_saa"] < 7.5 and 9.5 < a["gain_saa"] < 10.5


def test_the_shock_in_the_readme(v):
    a, b = v["Störungslagen selten"], v["Störungslagen häufig"]
    assert f"**{100 * a['window_saa']:.0f} %** (selten) bzw. **{100 * b['window_saa']:.0f} %** (häufig) der Reserve in das gefährdete Fenster, die Praxisregel **{100 * a['window_prop']:.0f} %**" in README
    assert f"nur **{a['blind_loss']:.1f} %** bzw. **{b['blind_loss']:.1f} %**" in README
    assert a["window_prop"] == pytest.approx(1 / 3, abs=0.05) and 0 < a["blind_loss"] < b["blind_loss"] < 2.0 and b["window_saa"] > a["window_saa"] > a["window_saa_blind"]


def test_the_planning_days_in_the_readme(v):
    names = ("25 Planungsszenarien", "50 Planungsszenarien", "100 Planungsszenarien", "400 Planungsszenarien")
    gains = [v[n]["gain_saa"] for n in names]
    assert "um **" + " / ".join(f"{g:.1f}" for g in gains) + " %**" in README and gains == sorted(gains)
    a, b = v["25 Planungsszenarien"], v["400 Planungsszenarien"]
    assert f"um **{pm(a['optimism'], a['optimism_se'])}** besser aus als die Wirklichkeit, bei 400 Tagen um **{pm(b['optimism'], b['optimism_se'])}**" in README and a["optimism"] > b["optimism"]


def test_trains_and_spielraum_in_the_readme(v):
    one, eight, g1, g4 = v["1 Zug"], v["8 Züge"], v["Spielraum 1 min"], v["Spielraum 4 min"]
    assert f"Mit 1 Zug senkt das Optimum die Verspätung um **{one['gain_saa']:.1f} %**, mit 8 Zügen um **{eight['gain_saa']:.1f} %**; bei 1 min Spielraum um **{g1['gain_saa']:.1f} %**, bei 4 min um **{g4['gain_saa']:.1f} %**" in README
    assert one["gain_saa"] < v["Standard"]["gain_saa"] < eight["gain_saa"] and g1["gain_saa"] < g4["gain_saa"]


def test_the_vorab_correction_is_consistent(v):
    assert "**20,5 %** über dem Optimum" in README and 14.0 < v["Standard"]["over_prop"] < 18.0                 # der Vorab-Wert liegt klar über dem hier gemessenen


def test_the_optimum_always_beats_the_rules_on_average(v):
    for name, x in v.items():
        assert x["delay_saa"] < x["delay_risk"] <= x["delay_prop"] + 0.05 and x["delay_none"] > x["delay_prop"], name


def test_mean_delay_is_ordered_in_every_row(res):
    for r in res["rows"]:
        m = r["methods"]
        assert m["none"]["delay"] > m["saa"]["delay"]                                                                  # mit Reserve ist es auf jeder Strecke besser als ohne


@pytest.mark.parametrize("name", C.PRESET_ORDER)
def test_every_preset_tells_its_story_on_the_shown_route(res, name):
    p = C.PRESETS[name]
    settings = {k: p[k] for k in ("budget", "trains", "gap", "score", "share", "corr", "data", "seed")}
    ref = E.run_live({**{k: C.PRESETS["Standard"][k] for k in ("budget", "trains", "gap", "score", "share", "corr", "data")}, "seed": p["seed"]})
    run = ref if name == "Standard" else E.run_live(settings)
    failed = [text for _, text, ok in S.check(name, S.facts_for(run, ref, res, settings)) if not ok]
    assert not failed, (name, failed)
