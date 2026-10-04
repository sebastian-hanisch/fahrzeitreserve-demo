"""AppTest-Rauchtests: Voreinstellung, jedes Preset, Randwerte, Würfel-Knopf, Permalink, Abschnitte, Exakt-Tab, Footer."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import rsv_constants as C

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _run(**state):
    at = AppTest.from_file(APP, default_timeout=300)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    return at


def _ok(at):
    assert not at.exception, [e.value for e in at.exception]


def _has_metric(at, label):
    return any(m.label == label for m in at.metric)


def _texts(at):
    return [x.value for x in list(at.success) + list(at.info) + list(at.warning)]


def test_default_run_has_no_exception_and_shows_the_three_methods():
    at = _run()
    _ok(at)
    for key in C.METHODS:
        assert _has_metric(at, C.METHOD_LABELS[key]), key
    assert not _has_metric(at, C.METHOD_LABELS["saa_blind"])
    s = at.session_state
    assert (s["budget_slider"], s["trains_select"], s["gap_select"], s["score_select"], s["share_select"], s["corr_select"], s["data_select"], s["seed_input"]) == (5, 5, 2, "alle", 0, "aus", 200, 500)
    assert any("Das Optimum senkt die mittlere Verspätung um" in t for t in _texts(at))


@pytest.mark.parametrize("name", C.PRESET_ORDER)
def test_every_preset_button_runs_and_sets_the_controls(name):
    at = _run()
    next(b for b in at.button if b.key == f"preset_{name}").click().run()
    _ok(at)
    p = C.PRESETS[name]
    s = at.session_state
    assert (s["budget_slider"], s["trains_select"], s["gap_select"], s["score_select"], s["share_select"], s["corr_select"], s["data_select"], s["seed_input"]) == \
        (p["budget"], p["trains"], p["gap"], p["score"], p["share"], p["corr"], p["data"], p["seed"])
    assert _has_metric(at, C.METHOD_LABELS["saa"])


def test_shock_preset_shows_the_blind_optimum_and_its_message():
    at = _run()
    next(b for b in at.button if b.key == "preset_Störungslagen").click().run()
    _ok(at)
    assert _has_metric(at, C.METHOD_LABELS["saa_blind"]) and any("Störungslagen: Das Optimum legt" in t for t in _texts(at))


def test_wenig_daten_preset_warns_about_self_deception():
    at = _run()
    next(b for b in at.button if b.key == "preset_Wenig Daten").click().run()
    _ok(at)
    assert any("Selbsttäuschung" in w.value for w in at.warning)


@pytest.mark.parametrize("kw", [dict(budget_slider=1), dict(budget_slider=10), dict(trains_select=1), dict(trains_select=8), dict(gap_select=1), dict(gap_select=4), dict(score_select="ende"),
                                 dict(score_select="last"), dict(share_select=50), dict(share_select=75), dict(corr_select="selten"), dict(corr_select="haeufig"), dict(data_select=25),
                                 dict(data_select=400), dict(seed_input=C.SEED_MIN), dict(seed_input=C.SEED_MAX), dict(view_select="prop"), dict(view_select="risk")])
def test_extreme_settings_run(kw):
    _ok(_run(**kw))


def test_other_settings_change_the_result_and_the_text():
    std = _run()
    ende = _run(score_select="ende")
    assert any("Es zählt nur die Endankunft" in t for t in _texts(ende)) and not any("Es zählt nur die Endankunft" in t for t in _texts(std))
    assert [m.value for m in std.metric][:3] != [m.value for m in ende.metric][:3]


def test_dice_button_changes_the_seed():
    at = _run()
    old = at.session_state["seed_input"]
    next(b for b in at.button if b.label == "🎲 Neue Strecke würfeln").click().run()
    _ok(at)
    assert at.session_state["seed_input"] != old


def test_permalink_values_are_clamped_and_snapped():
    at = AppTest.from_file(APP, default_timeout=300)
    for k, v in (("budget", "99"), ("trains", "4"), ("gap", "3"), ("score", "last"), ("share", "60"), ("corr", "selten"), ("data", "75"), ("seed", "99999"), ("view", "risk")):
        at.query_params[k] = v
    at.run()
    _ok(at)
    s = at.session_state
    assert (s["budget_slider"], s["trains_select"], s["gap_select"], s["score_select"], s["share_select"], s["corr_select"], s["data_select"], s["seed_input"], s["view_select"]) == \
        (10, 3, 2, "last", 50, "selten", 50, C.SEED_MAX, "risk")


def test_permalink_ignores_garbage_and_roundtrips():
    at = AppTest.from_file(APP, default_timeout=300)
    at.query_params["budget"] = "viel"
    at.query_params["score"] = "unbekannt"
    at.query_params["view"] = "xyz"
    at.run()
    _ok(at)
    s = at.session_state
    assert s["budget_slider"] == C.DEFAULT_BUDGET and s["score_select"] == C.DEFAULT_SCORE and s["view_select"] == C.DEFAULT_VIEW
    next(b for b in at.button if b.key == "preset_Störungslagen").click().run()
    qp = at.query_params
    at2 = AppTest.from_file(APP, default_timeout=300)
    for k in ("budget", "trains", "gap", "score", "share", "corr", "data", "seed", "view"):
        v = qp[k]
        at2.query_params[k] = v[0] if isinstance(v, list) else v
    at2.run()
    _ok(at2)
    assert at2.session_state["corr_select"] == "haeufig"


def test_sections_expanders_and_charts_are_present():
    at = _run()
    _ok(at)
    headers = [s.value for s in at.subheader] + [m.value for m in at.markdown]
    assert any("Was die Messreihe zeigt" in h for h in headers) and any("Wo gehört die Reserve hin" in h for h in headers)
    titles = [e.label for e in at.expander]
    assert "🔧 Wie wir das erreichen – vollständiger Methodenvergleich" in titles and "Wie funktioniert diese Demo?" in titles and "📐 Mathematische Formulierung" in titles
    assert [t.label for t in at.tabs] == ["📏 Verfahren", "🧮 Optimum (lineares Programm)", "📈 Messreihe"]
    assert len(at.get("plotly_chart")) == 7          # Reserve je Abschnitt, Verspätungsprofil, Verfahren, vier Messreihen-Diagramme


def test_exact_tab_solves_the_lp_with_more_planning_days():
    at = _run(trains_select=1)
    _ok(at)
    next(b for b in at.button if b.key == "exact_button").click().run()
    _ok(at)
    assert _has_metric(at, "Planungstage versprechen") and any(m.label.startswith("Optimum mit 1000 Tagen") for m in at.metric)
    at.select_slider(key="trains_select").set_value(3).run()
    assert not _has_metric(at, "Planungstage versprechen") and any("erneut lösen" in c.value for c in at.caption)


def test_seed_control_uses_the_portfolio_wording():
    assert [n.label for n in _run().number_input] == ["Zufalls-Seed"]


def test_related_demos_are_linked_and_footer_is_present():
    at = _run()
    text = " ".join(c.value for c in at.caption)
    for name in ("taktfahrplan-demo", "streckenkonflikt-demo", "bullwhip-demo", "robuste-kaiplatz-demo"):
        assert name in text
    assert "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net)" in text
    assert "geplant" not in text and "noch nicht" not in text
