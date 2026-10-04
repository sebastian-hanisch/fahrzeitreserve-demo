"""Diagramm-Werte, Markierungen und feste Achsen der Figuren."""
import pytest

import rsv_constants as C
import rsv_results as R
import rsv_visualization as V
from test_evaluation import fake
from test_results import RES


def run(**kw):
    r = fake(**kw)
    r["cfg"]["r"] = [10, 11, 12, 13, 14, 15, 16, 4, 5, 6, 7, 8]
    return r


def test_allocation_bars_show_minutes_and_label_the_sections():
    fig = V.build_allocation_bars(run())
    assert [t.name for t in fig.data] == [C.METHOD_LABELS["prop"], C.METHOD_LABELS["risk"], C.METHOD_LABELS["saa"]]
    assert list(fig.data[0].y) == [0.6] * 12 and list(fig.data[2].y) == [0, 0, 1.0, 3.0, 0, 0, 0, 1.0, 2.0, 0, 0, 0]
    assert fig.layout.xaxis.ticktext[0] == "1<br>10 min"
    assert fig.layout.xaxis.ticktext[3] == "4<br>13 min<br>Engpass" and fig.layout.xaxis.ticktext[11] == "12<br>8 min<br>Engpass" and fig.layout.xaxis.ticktext[2] == "3<br>12 min"
    assert len(fig.layout.shapes) == 0


def test_a_shock_adds_the_window_and_the_blind_optimum():
    r = run(blind=1.8, w0=2)
    r["corr"] = "haeufig"
    fig = V.build_allocation_bars(r)
    assert [t.name for t in fig.data][-1] == C.METHOD_LABELS["saa_blind"] and len(fig.data) == 4
    assert len(fig.layout.shapes) == 1 and fig.layout.shapes[0].x0 == 1.5 and fig.layout.shapes[0].x1 == 5.5


def test_method_keys_include_the_blind_optimum_only_when_present():
    assert V.method_keys(run()) == ["prop", "risk", "saa"] and V.method_keys(run(blind=1.8)) == ["prop", "risk", "saa", "saa_blind"]


def test_delay_profile_has_the_reference_line_and_one_line_per_method():
    r = run()
    r["results"]["saa"]["profile"] = [float(k) for k in range(12)]
    fig = V.build_delay_profile(r)
    assert [t.name for t in fig.data] == ["ohne Reserve", C.METHOD_LABELS["prop"], C.METHOD_LABELS["risk"], C.METHOD_LABELS["saa"]]
    assert list(fig.data[3].y) == [float(k) for k in range(12)] and list(fig.data[3].x) == list(range(1, 13))


def test_method_bars_show_delay_and_punctuality_in_a_fixed_order():
    fig = V.build_method_bars(run())
    assert list(fig.data[0].x) == ["ohne Reserve", C.METHOD_LABELS["prop"], C.METHOD_LABELS["risk"], C.METHOD_LABELS["saa"]]
    assert list(fig.data[0].y) == [3.0, 2.0, 1.8, 1.6] and list(fig.data[0].text) == ["70 % pünktlich", "80 % pünktlich", "80 % pünktlich", "85 % pünktlich"]


def test_budget_curve_is_sorted_by_budget_and_uses_the_gain():
    rows = R.all_variants({"meta": {"variants": ["Budget 3 %", "Standard", "Budget 1 %"]}, "rows": [dict(RES["rows"][0], variant="Standard"), dict(RES["rows"][1], variant="Standard"),
                                                                                                   dict(RES["rows"][4], variant="Budget 1 %"), dict(RES["rows"][0], variant="Budget 3 %"),
                                                                                                   dict(RES["rows"][1], variant="Budget 3 %")]})
    fig = V.build_budget_curve(rows)
    assert list(fig.data[0].x) == [1, 3, 5] and list(fig.data[0].y) == [rows[2]["gain_saa"], rows[0]["gain_saa"], rows[1]["gain_saa"]]


def test_sweep_figures_use_the_mean_values():
    rows = R.all_variants(RES)
    f = V.build_variant_bars(rows)
    assert [t.name for t in f.data] == [C.METHOD_LABELS["prop"], C.METHOD_LABELS["risk"]] and list(f.data[0].y) == [rows[0]["over_prop"], rows[1]["over_prop"]]
    m = V.build_mean_allocation(RES, "Standard")
    assert [t.name for t in m.data] == [C.METHOD_LABELS["prop"], C.METHOD_LABELS["risk"], C.METHOD_LABELS["saa"]] and list(m.data[2].y) == [0.0, 50.0, 50.0, 0.0] and list(m.data[0].y) == [25.0] * 4


def test_data_curve_plots_optimism_as_a_positive_self_deception():
    base = R.summary(RES, "Standard")
    pts = [{"name": "a", "data": 25, **base, "optimism": 5.0, "gain_saa": 12.0}, {"name": "b", "data": 200, **base, "optimism": -2.0, "gain_saa": 14.0}]
    fig = V.build_data_curve(pts)
    assert list(fig.data[0].x) == [25, 200] and list(fig.data[0].y) == [12.0, 14.0] and list(fig.data[1].y) == [-5.0, 2.0]


@pytest.mark.parametrize("make", [lambda: V.build_allocation_bars(run()), lambda: V.build_delay_profile(run()), lambda: V.build_method_bars(run()), lambda: V.build_variant_bars(R.all_variants(RES)),
                                  lambda: V.build_mean_allocation(RES, "Standard")])
def test_all_axes_are_fixed_for_touch_scrolling(make):
    fig = make()
    assert fig.layout.xaxis.fixedrange is True and fig.layout.yaxis.fixedrange is True
