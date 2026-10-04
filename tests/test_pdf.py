"""Reserveplan als PDF: gültige Datei, Kernschrift-Bereinigung."""
import rsv_model as M
import rsv_pdf_export as P


def test_pdf_is_a_valid_document_for_every_method():
    cfg = M.make_config(500)
    for name in ("prop", "risk"):
        a = M.method_allocation(name, cfg, 7, 0)
        data = P.generate_plan_pdf(cfg, a.tolist(), "Reserveplan", ["12 Abschnitte – 7 min", "Zeit ≥ 3 min"])
        assert data.startswith(b"%PDF") and data.rstrip().endswith(b"%%EOF") and len(data) > 1000


def test_clean_replaces_characters_the_core_font_cannot_draw():
    assert P._clean("A – B ≥ C → D … € Ø") == "A - B >= C -> D ... EUR Durchschnitt"
    assert P._clean("Größe äöüß") == "Größe äöüß" and P._clean("Emoji 🚆") == "Emoji ?"


def test_table_rows_show_tenth_minutes_and_mark_the_bottlenecks():
    import numpy as np
    cfg = {"n": 2, "r": np.array([10, 20]), "bott": (1,)}
    assert P.table_rows(cfg, [5, 15]) == ["1 | 10 | 0.5 | 10.5", "2 | 20 | 1.5 | 21.5  (Engpass)"]
    assert P.table_rows(cfg, [0, 0]) == ["1 | 10 | 0.0 | 10.0", "2 | 20 | 0.0 | 20.0  (Engpass)"]
