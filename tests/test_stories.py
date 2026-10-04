"""Preset-Kriterien: jedes Kriterium kippt einzeln an seiner Schwelle (künstliche Zahlen), und `facts_for` liest die richtigen Größen."""
import pytest

import rsv_constants as C
import rsv_evaluation as E
import rsv_results as R
import rsv_stories as S

BASE = dict(gain=14.0, over=16.0, ref_gain=14.0, ref_over=16.0, used=4, zero_sections=8, centroid=44.0, end_share=40.0, optimism=1.0, data=200, budget_min=7.0, window_saa=30.0, window_prop=33.0,
            blind_delay=None, sweep_gain=13.6, sweep_zero=0.59, sweep_over=15.9, sweep_centroid=43.0, sweep_optimism=0.1, sweep_blind_loss=0.5, sweep_window=0.6, sweep_std_gain=13.6)

GOOD = {
    "Standard": {},
    "Nur Endankunft": dict(end_share=100.0, over=60.0, sweep_over=56.0, sweep_centroid=99.0),
    "Mindestanteil": dict(zero_sections=0, gain=7.0, sweep_gain=6.9),
    "Störungslagen": dict(window_saa=63.0, window_prop=33.0, blind_delay=1.5, sweep_blind_loss=0.8, sweep_window=0.63),
    "Wenig Daten": dict(data=25, optimism=6.0, sweep_optimism=4.8, sweep_gain=11.4),
    "Knappes Budget": dict(gain=5.0, sweep_gain=5.1, budget_min=1.4),
}

BREAK = {
    "Standard": {"gain": dict(gain=9.9), "few_sections": dict(used=7), "interior": dict(centroid=70.0), "sweep_gain": dict(sweep_gain=11.9), "sweep_zero": dict(sweep_zero=0.5)},
    "Nur Endankunft": {"end": dict(end_share=80.0), "rule_far": dict(over=29.0, ref_over=10.0), "more_than_standard": dict(ref_over=70.0), "sweep_over": dict(sweep_over=39.0),
                       "sweep_centroid": dict(sweep_centroid=85.0)},
    "Mindestanteil": {"floor": dict(zero_sections=1), "smaller_gain": dict(gain=14.0, ref_gain=14.0), "still_positive": dict(gain=0.0), "sweep_small": dict(sweep_gain=8.5)},
    "Störungslagen": {"window": dict(window_saa=49.0, window_prop=20.0), "window_more": dict(window_prop=50.0, window_saa=60.0), "blind_exists": dict(blind_delay=None),
                      "sweep_small_loss": dict(sweep_blind_loss=2.0), "sweep_window": dict(sweep_window=0.5)},
    "Wenig Daten": {"few": dict(data=50), "warning": dict(optimism=4.9), "sweep_optimism": dict(sweep_optimism=3.0), "sweep_less": dict(sweep_gain=13.6)},
    "Knappes Budget": {"small_gain": dict(gain=7.0, ref_gain=7.0), "small": dict(gain=8.0, ref_gain=14.0), "sweep_small": dict(sweep_gain=8.0), "budget_small": dict(budget_min=2.1)},
}


def facts(preset, **over):
    return {**BASE, **GOOD[preset], **over}


def failing(preset, **over):
    return [cid for cid, _, ok in S.check(preset, facts(preset, **over)) if not ok]


def test_every_preset_has_criteria_and_breakers_for_each_of_them():
    assert set(S.CRITERIA) == set(C.PRESET_ORDER) == set(GOOD) == set(BREAK)
    for name in C.PRESET_ORDER:
        assert {cid for cid, _, _ in S.CRITERIA[name]} == set(BREAK[name]), name


@pytest.mark.parametrize("preset", C.PRESET_ORDER)
def test_good_facts_pass_every_criterion(preset):
    assert failing(preset) == []


@pytest.mark.parametrize("preset,cid", [(p, c) for p in C.PRESET_ORDER for c in BREAK[p]])
def test_each_criterion_flips_alone(preset, cid):
    assert failing(preset, **BREAK[preset][cid]) == [cid]


def test_thresholds_are_exact():
    assert failing("Standard", gain=10.0) == [] and failing("Standard", gain=9.99) == ["gain"]
    assert failing("Standard", used=6) == [] and failing("Standard", used=7) == ["few_sections"]
    assert failing("Standard", centroid=25.0) == [] and failing("Standard", centroid=65.0) == [] and failing("Standard", centroid=24.9) == ["interior"] and failing("Standard", centroid=65.1) == ["interior"]
    assert failing("Standard", sweep_gain=12.0) == [] and failing("Standard", sweep_zero=0.51) == [] and failing("Standard", sweep_zero=0.5) == ["sweep_zero"]
    assert failing("Nur Endankunft", over=30.0) == [] and failing("Nur Endankunft", sweep_over=40.0) == [] and failing("Nur Endankunft", sweep_centroid=90.0) == []
    assert failing("Störungslagen", window_saa=50.0, window_prop=35.0) == [] and failing("Störungslagen", window_saa=60.0, window_prop=45.0) == [] and failing("Störungslagen", window_saa=60.0, window_prop=45.1) == ["window_more"]
    assert failing("Störungslagen", sweep_blind_loss=1.99) == [] and failing("Störungslagen", sweep_window=0.51) == []
    assert failing("Wenig Daten", optimism=5.0) == [] and failing("Wenig Daten", sweep_optimism=3.01) == []
    assert failing("Knappes Budget", gain=7.99) == [] and failing("Knappes Budget", budget_min=2.0) == [] and failing("Knappes Budget", sweep_gain=7.99) == []
    assert failing("Mindestanteil", sweep_gain=8.0) == [] and failing("Mindestanteil", gain=0.01) == []


def test_missing_sweep_values_fail_the_sweep_criteria():
    nan = float("nan")
    assert failing("Standard", sweep_gain=nan) == ["sweep_gain"] and failing("Störungslagen", sweep_blind_loss=nan, sweep_window=nan) == ["sweep_small_loss", "sweep_window"]


def test_facts_for_reads_the_live_run_and_the_sweep():
    res = R.load_results()
    p = C.PRESETS["Standard"]
    settings = {k: p[k] for k in ("budget", "trains", "gap", "score", "share", "corr", "data", "seed")}
    run = E.run_live(settings)
    f = S.facts_for(run, run, res, settings)
    assert f["used"] == 4 and f["zero_sections"] == 8 and f["data"] == 200 and f["budget_min"] == 7.0 and f["blind_delay"] is None
    assert f["gain"] == pytest.approx(E.gain_pct(run)) and f["over"] == pytest.approx(E.over_pct(run)) and f["ref_gain"] == f["gain"]
    assert f["end_share"] == 0.0 and f["centroid"] == pytest.approx(E.centroid_pct([0, 0, 10, 30, 0, 0, 0, 10, 20, 0, 0, 0]))              # die letzten beiden Abschnitte haben keine Reserve
    v = R.summary(res, "Standard")
    assert f["sweep_gain"] == v["gain_saa"] and f["sweep_zero"] == v["zero_share"] and f["sweep_over"] == v["over_prop"] and f["sweep_centroid"] == pytest.approx(100 * v["centroid_saa"])
    assert f["sweep_std_gain"] == v["gain_saa"] and f["window_saa"] == pytest.approx(E.window_pct(run["results"]["saa"]["alloc"], run["cfg"]["w0"]))


def test_facts_for_without_a_sweep_variant_uses_neutral_values():
    res = R.load_results()
    settings = {"budget": 2, "trains": 5, "gap": 2, "score": "alle", "share": 0, "corr": "aus", "data": 200, "seed": 500}
    run = E.run_live(settings)
    f = S.facts_for(run, run, res, settings)
    assert f["sweep_gain"] != f["sweep_gain"] and f["sweep_std_gain"] == R.summary(res, "Standard")["gain_saa"]


def test_facts_for_reads_the_shock_values():
    res = R.load_results()
    p = C.PRESETS["Störungslagen"]
    settings = {k: p[k] for k in ("budget", "trains", "gap", "score", "share", "corr", "data", "seed")}
    run = E.run_live(settings)
    f = S.facts_for(run, run, res, settings)
    assert f["blind_delay"] == run["results"]["saa_blind"]["delay"] and f["sweep_blind_loss"] == R.summary(res, "Störungslagen häufig")["blind_loss"]
