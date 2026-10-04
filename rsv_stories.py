"""Abnahmekriterien der Presets: jedes Preset erzählt eine Geschichte, die an der gezeigten Strecke UND an der Messreihe überprüfbar ist.

Reine Funktionen einfacher Zahlen (`check`), damit Tests sie mit künstlichen Werten einzeln an ihrer Schwelle kippen können; `facts_for` baut die Zahlen aus einer Live-Rechnung, dem Standard-Lauf
auf derselben Strecke und der Ergebnisdatei. `tools/preset_search.py` sucht damit einen Seed außerhalb der Messreihen-Seeds, bei dem alle Kriterien aller Presets gelten.
"""
from __future__ import annotations

import rsv_constants as C
import rsv_evaluation as E
import rsv_results as R

CRITERIA = {
    "Standard": [
        ("gain", "Das Optimum senkt die Verspätung um mindestens 10 % gegenüber der Praxisregel", lambda f: f["gain"] >= 10.0),
        ("few_sections", "Das Optimum legt die Reserve in höchstens 6 Abschnitte", lambda f: f["used"] <= 6),
        ("interior", "Der Schwerpunkt der optimalen Reserve liegt zwischen 25 % und 65 % der Strecke", lambda f: 25.0 <= f["centroid"] <= 65.0),
        ("sweep_gain", "Messreihe: das Optimum senkt die Verspätung im Mittel um mindestens 12 %", lambda f: f["sweep_gain"] >= 12.0),
        ("sweep_zero", "Messreihe: das Optimum lässt im Mittel mehr als die Hälfte der Abschnitte ohne Reserve", lambda f: f["sweep_zero"] > 0.5),
    ],
    "Nur Endankunft": [
        ("end", "Das Optimum legt die ganze Reserve in die letzten beiden Abschnitte", lambda f: f["end_share"] >= 99.9),
        ("rule_far", "Die Praxisregel liegt mindestens 30 % über dem Optimum", lambda f: f["over"] >= 30.0),
        ("more_than_standard", "Der Abstand der Praxisregel ist größer als im Standardfall", lambda f: f["over"] > f["ref_over"]),
        ("sweep_over", "Messreihe: die Praxisregel liegt im Mittel mindestens 40 % über dem Optimum", lambda f: f["sweep_over"] >= 40.0),
        ("sweep_centroid", "Messreihe: der Schwerpunkt der optimalen Reserve liegt bei mindestens 90 % der Strecke", lambda f: f["sweep_centroid"] >= 90.0),
    ],
    "Mindestanteil": [
        ("floor", "Jeder Abschnitt bekommt Reserve", lambda f: f["zero_sections"] == 0),
        ("smaller_gain", "Der Vorsprung des Optimums ist kleiner als im Standardfall", lambda f: f["gain"] < f["ref_gain"]),
        ("still_positive", "Das Optimum liegt noch vor der Praxisregel", lambda f: f["gain"] > 0.0),
        ("sweep_small", "Messreihe: das Optimum senkt die Verspätung im Mittel um höchstens 8 %", lambda f: f["sweep_gain"] <= 8.0),
    ],
    "Störungslagen": [
        ("window", "Das Optimum legt mindestens die Hälfte der Reserve in das gefährdete Fenster", lambda f: f["window_saa"] >= 50.0),
        ("window_more", "Das Optimum legt mindestens 15 Punkte mehr in das Fenster als die Praxisregel", lambda f: f["window_saa"] - f["window_prop"] >= 15.0),
        ("blind_exists", "Das Optimum ohne Störungslagen liegt in den Ergebnissen", lambda f: f["blind_delay"] is not None),
        ("sweep_small_loss", "Messreihe: wer Störungslagen nicht kennt, verliert im Mittel weniger als 2 %", lambda f: f["sweep_blind_loss"] < 2.0),
        ("sweep_window", "Messreihe: das Optimum legt im Mittel mehr als die Hälfte der Reserve ins Fenster", lambda f: f["sweep_window"] > 0.5),
    ],
    "Wenig Daten": [
        ("few", "Es sind nur 25 Planungstage", lambda f: f["data"] == 25),
        ("warning", "Die Planungstage versprechen mindestens 5 % mehr, als frische Tage halten", lambda f: f["optimism"] >= 5.0),
        ("sweep_optimism", "Messreihe: die Selbsttäuschung liegt bei 25 Planungstagen im Mittel über 3 %", lambda f: f["sweep_optimism"] > 3.0),
        ("sweep_less", "Messreihe: der Vorsprung ist kleiner als im Standardfall", lambda f: f["sweep_gain"] < f["sweep_std_gain"]),
    ],
    "Knappes Budget": [
        ("small_gain", "Der Vorsprung des Optimums ist kleiner als im Standardfall", lambda f: f["gain"] < f["ref_gain"]),
        ("small", "Das Optimum senkt die Verspätung um weniger als 8 %", lambda f: f["gain"] < 8.0),
        ("sweep_small", "Messreihe: das Optimum senkt die Verspätung im Mittel um weniger als 8 %", lambda f: f["sweep_gain"] < 8.0),
        ("budget_small", "Das Budget ist höchstens 2 Minuten", lambda f: f["budget_min"] <= 2.0),
    ],
}


def facts_for(run: dict, ref: dict, res: dict, settings: dict) -> dict:
    """Die Zahlen für die Kriterien. `ref` = Lauf mit den Standardreglern auf demselben Seed."""
    r = run["results"]
    alloc = r["saa"]["alloc"]
    vname = R.variant_name(settings)
    sw = R.summary(res, vname) if vname else None
    std = R.summary(res, "Standard")
    f = {"gain": E.gain_pct(run), "over": E.over_pct(run), "ref_gain": E.gain_pct(ref), "ref_over": E.over_pct(ref), "used": sum(1 for x in alloc if x > 0), "zero_sections": sum(1 for x in alloc if x == 0),
         "centroid": E.centroid_pct(alloc), "end_share": 100 * sum(alloc[-2:]) / sum(alloc), "optimism": E.optimism_pct(run), "data": settings["data"], "budget_min": run["B"] / C.UNITS_PER_MIN,
         "window_saa": E.window_pct(alloc, run["cfg"]["w0"]), "window_prop": E.window_pct(r["prop"]["alloc"], run["cfg"]["w0"]),
         "blind_delay": r["saa_blind"]["delay"] if "saa_blind" in r else None}
    f.update({k: float("nan") for k in ("sweep_gain", "sweep_zero", "sweep_over", "sweep_centroid", "sweep_optimism", "sweep_blind_loss", "sweep_window")})
    f["sweep_std_gain"] = std["gain_saa"]
    if sw:
        f.update({"sweep_gain": sw["gain_saa"], "sweep_zero": sw["zero_share"], "sweep_over": sw["over_prop"], "sweep_centroid": 100 * sw["centroid_saa"], "sweep_optimism": sw["optimism"],
                  "sweep_blind_loss": sw.get("blind_loss", float("nan")), "sweep_window": sw.get("window_saa", float("nan"))})
    return f


def check(preset: str, facts: dict) -> list:
    """Liste (Kennung, Text, erfüllt) der Kriterien eines Presets."""
    return [(cid, text, bool(fn(facts))) for cid, text, fn in CRITERIA[preset]]
