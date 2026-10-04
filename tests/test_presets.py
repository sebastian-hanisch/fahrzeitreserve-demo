"""Permalink-Einrasten, Presets und Konstanten-Konsistenz."""
import rsv_constants as C
import rsv_presets as PR
import rsv_results as R


def test_snap_rounds_to_the_nearest_option_and_prefers_the_smaller_on_ties():
    assert PR.snap(C.TRAINS_OPTIONS, 4) == 3 and PR.snap(C.TRAINS_OPTIONS, 6) == 5 and PR.snap(C.TRAINS_OPTIONS, 99) == 8 and PR.snap(C.TRAINS_OPTIONS, 0) == 1
    assert PR.snap(C.DATA_OPTIONS, 75) == 50 and PR.snap(C.DATA_OPTIONS, 150) == 100 and PR.snap(C.SHARE_OPTIONS, 60) == 50 and PR.snap(C.GAP_OPTIONS, 3) == 2


def test_every_preset_sets_every_control_with_valid_values():
    assert set(C.PRESET_ORDER) == set(C.PRESETS) == set(C.PRESET_HELP) and len(C.PRESET_ORDER) == 6
    for name, p in C.PRESETS.items():
        assert set(p) == set(PR.PRESET_KEYS)
        assert C.BUDGET_MIN <= p["budget"] <= C.BUDGET_MAX and p["trains"] in C.TRAINS_OPTIONS and p["gap"] in C.GAP_OPTIONS and p["score"] in C.SCORE_OPTIONS
        assert p["share"] in C.SHARE_OPTIONS and p["corr"] in C.CORR_OPTIONS and p["data"] in C.DATA_OPTIONS
        assert C.SEED_MIN <= p["seed"] <= C.SEED_MAX and not (C.SWEEP_SEEDS.start <= p["seed"] < C.SWEEP_SEEDS.stop), name


def test_each_non_standard_preset_changes_the_lever_it_is_named_for():
    std = C.PRESETS["Standard"]
    changed = {n: sorted(k for k in std if k != "seed" and C.PRESETS[n][k] != std[k]) for n in C.PRESET_ORDER if n != "Standard"}
    assert changed == {"Nur Endankunft": ["score"], "Mindestanteil": ["share"], "Störungslagen": ["corr"], "Wenig Daten": ["data"], "Knappes Budget": ["budget"]}
    assert len({p["seed"] for p in C.PRESETS.values()}) == 1 and std["seed"] == C.DEFAULT_SEED


def test_every_preset_matches_a_sweep_variant():
    names = {n: R.variant_name({k: C.PRESETS[n][k] for k in PR.PRESET_KEYS if k != "seed"}) for n in C.PRESET_ORDER}
    assert names == {"Standard": "Standard", "Nur Endankunft": "Wertung Endankunft", "Mindestanteil": "Mindestanteil 75 %", "Störungslagen": "Störungslagen häufig",
                     "Wenig Daten": "25 Planungsszenarien", "Knappes Budget": "Budget 1 %"}


def test_view_options_are_methods_and_settings_convert():
    assert set(C.VIEW_OPTIONS) <= set(C.METHOD_LABELS) and set(C.METHODS) <= set(C.METHOD_LABELS) and set(C.METHOD_COLORS) == set(C.METHOD_LABELS)
    s = PR.settings_from_state({"budget_slider": 5, "trains_select": 5, "gap_select": 2, "score_select": "alle", "share_select": 0, "corr_select": "aus", "data_select": 200, "seed_input": 500.0})
    assert s == {"budget": 5, "trains": 5, "gap": 2, "score": "alle", "share": 0, "corr": "aus", "data": 200, "seed": 500}


def test_corr_labels_and_permille_cover_the_options():
    assert set(C.CORR_LABELS) == set(C.CORR_PERMILLE) == set(C.CORR_OPTIONS) and set(C.SCORE_LABELS) == set(C.SCORE_OPTIONS)
    assert C.CORR_PERMILLE["aus"] == 0 and C.CORR_PERMILLE["selten"] < C.CORR_PERMILLE["haeufig"]
