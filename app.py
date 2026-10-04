"""Fahrzeitreserve: Wo setzt man den Puffer? - interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Fünfter Baustein der Reihe Bahn/Schienenverkehr: Ein festes Budget an Fahrzeitreserve (Minuten) wird auf die Abschnitte einer Strecke verteilt, auf der mehrere Züge hintereinander fahren und
zufällig gestört werden. Die Demo vergleicht die Praxisregel (proportional zur Fahrzeit) mit einer risikoproportionalen Regel und dem Optimum nach Planungstagen (lineares Programm), und zeigt,
wie stark die Antwort davon abhängt, wo Verspätung gezählt wird.

Lauffähig mit: streamlit run app.py
"""

import pandas as pd
import streamlit as st

import rsv_constants as C
import rsv_model as M
import rsv_results as R
import rsv_saa as S
from rsv_evaluation import messages, run_live
from rsv_pdf_export import generate_plan_pdf
from rsv_presets import (apply_preset, bounds, init_session_state_defaults, load_permalink_settings, randomize_seed, settings_from_state,
                         sync_query_params)
from rsv_visualization import (build_allocation_bars, build_budget_curve, build_data_curve, build_delay_profile, build_mean_allocation, build_method_bars,
                               build_variant_bars)

st.set_page_config(page_title="Fahrzeitreserve – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner=False)
def _results():
    return R.load_results()


@st.cache_data(show_spinner=False)
def _live(budget, trains, gap, score, share, corr, data, seed):
    return run_live({"budget": budget, "trains": trains, "gap": gap, "score": score, "share": share, "corr": corr, "data": data, "seed": seed})


st.title("🚆 Fahrzeitreserve: Wo setzt man den Puffer?")
st.markdown(
    """
Auf einer **Strecke mit zwölf Abschnitten** fahren mehrere Züge hintereinander und werden zufällig gestört. Im Fahrplan darf **ein festes Budget an Reserve** (Prozent der Fahrzeit, in Zehntelminuten verteilt) auf die Abschnitte
verteilt werden; jede Reserve nimmt Verspätung auf, die sich sonst entlang der Strecke und auf die Folgezüge überträgt. Die Demo vergleicht die **Praxisregel** (proportional zur Fahrzeit) mit einer
**risikoproportionalen Regel** und dem **Optimum nach Planungstagen** (lineares Programm) und beantwortet drei Fragen: **Wie viel verschenkt die Praxisregel?**, **Wo gehört die Reserve hin?** und
**Wie sehr hängt die Antwort davon ab, wo Verspätung gezählt wird und wie viele Tage man beobachtet hat?**
"""
)
st.caption(
    "Fünfter Baustein der Reihe Bahn/Schienenverkehr nach [Taktfahrplan](https://sebastianhanisch-taktfahrplan-demo.streamlit.app/) und "
    "[Trassenkonflikt](https://sebastianhanisch-streckenkonflikt-demo.streamlit.app/), in denen Fahrzeitreserven bewusst offen blieben. Die Verspätungsfortpflanzung entlang einer Kette kennt man aus "
    "[bullwhip-demo](https://sebastianhanisch-bullwhip-demo.streamlit.app/); neu ist hier das Verteilen eines festen Budgets. Verwandt: "
    "[robuste-kaiplatz-demo](https://sebastianhanisch-robuste-kaiplatz-demo.streamlit.app/) (ein Gesamtpuffer gegen Neuplanung)."
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
preset_cols = st.columns(3)
for i, name in enumerate(C.PRESET_ORDER):
    with preset_cols[i % 3]:
        st.button(name, key=f"preset_{name}", width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.slider("Reservebudget (% der Fahrzeit)", C.BUDGET_MIN, C.BUDGET_MAX, key="budget_slider",
              help="Gesamte Reserve in Prozent der planmäßigen Fahrzeit, in ganzen Minuten gerundet auf 0,1 min; sie wird auf die Abschnitte verteilt.")
    st.select_slider("Züge hintereinander", options=C.TRAINS_OPTIONS, key="trains_select",
                     help="Zahl der Züge, die dieselbe Strecke nacheinander befahren. Mit mehr Zügen überträgt sich Verspätung stärker.")
    st.select_slider("Zugfolge-Spielraum", options=C.GAP_OPTIONS, key="gap_select", format_func=lambda m: f"{m} min",
                     help="Geplanter Abstand minus Mindestzugfolge an den meisten Abschnittsenden. An zwei Engpässen ist er null: Jede Verspätung des Vorderzugs wird weitergegeben.")
    st.select_slider("Wo zählt Verspätung?", options=C.SCORE_OPTIONS, key="score_select", format_func=lambda s: C.SCORE_LABELS[s],
                     help="Die Wertung der Verspätung: an allen Halten gleich, nur am Ziel, oder mit mehr Gewicht in der Streckenmitte (Fahrgastlast).")
    st.select_slider("Mindestanteil je Abschnitt", options=C.SHARE_OPTIONS, key="share_select", format_func=lambda p: f"{p} %",
                     help="Kein Abschnitt darf weniger als diesen Prozentsatz seines proportionalen Anteils bekommen (praxisnahe Untergrenze). 0 % = freie Verteilung.")
    st.select_slider("Gemeinsame Störungslage", options=C.CORR_OPTIONS, key="corr_select", format_func=lambda c: C.CORR_LABELS[c],
                     help="An einem Teil der Tage sind vier benachbarte Abschnitte für alle Züge dreimal so störanfällig (Wetter, Baustelle). Dann ist die Verspätung der Züge eines Tages verbunden.")
    st.select_slider("Planungstage (Szenarien)", options=C.DATA_OPTIONS, key="data_select",
                     help="Wie viele beobachtete Tage das Optimum für seine Rechnung bekommt. Bewertet wird immer an frischen Tagen.")
    st.number_input("Zufalls-Seed", min_value=bounds("seed_input")[0], max_value=bounds("seed_input")[1], step=1, key="seed_input",
                    help="Bestimmt die Strecke: Fahrzeiten, Störanfälligkeit, Engpässe und das Fenster der Störungslage.")
    st.button("🎲 Neue Strecke würfeln", on_click=randomize_seed)

values = {k: st.session_state[k] for k in ("budget_slider", "trains_select", "gap_select", "score_select", "share_select", "corr_select", "data_select", "seed_input", "view_select")}
sync_query_params(values)
settings = settings_from_state(values)

res = _results()
with st.spinner(f"Rechne das Optimum aus {settings['data']} Planungstagen (lineares Programm) …"):
    run = _live(settings["budget"], settings["trains"], settings["gap"], settings["score"], settings["share"], settings["corr"], settings["data"], settings["seed"])
cfg, results = run["cfg"], run["results"]
vname = R.variant_name(settings)
st.caption(
    f"Strecke mit {cfg['n']} Abschnitten und {int(cfg['r'].sum())} min Fahrzeit, Budget {run['B'] / C.UNITS_PER_MIN:.1f} min Reserve; Engpässe an den Abschnitten {', '.join(str(k + 1) for k in cfg['bott'])}. "
    f"Rechenzeit dieses Laufs {run['seconds']:.1f} s (beim ersten Aufruf; danach aus dem Zwischenspeicher)."
)

st.markdown("---")
st.markdown("## 🚆 Wo gehört die Reserve hin – und was verschenkt die Praxisregel?")
cols = st.columns(4 if "saa_blind" in results else 3)
for col, key in zip(cols, [k for k in ("prop", "risk", "saa", "saa_blind") if k in results]):
    delta = None if key == "prop" else f"{100 * (results[key]['delay'] / results['prop']['delay'] - 1):+.0f} % gegen Praxisregel"
    col.metric(C.METHOD_LABELS[key], f"{results[key]['delay']:.2f} min", delta=delta, delta_color="inverse",
               help="Mittlere gewichtete Verspätung an frischen Tagen (nicht den Planungstagen). Delta = dieser Wert gegen die Praxisregel.")
for state, text in messages(run, settings):
    (st.success if state == "success" else st.warning if state == "warning" else st.info)(f"💡 {text}")

rows = []
for key in ("none", "prop", "risk", "saa", "saa_blind"):
    if key in results:
        r = results[key]
        rows.append({"Verfahren": "ohne Reserve" if key == "none" else C.METHOD_LABELS[key], "Verspätung (min)": round(r["delay"], 2), "pünktlich (≤ 3 min)": f"{100 * r['punct']:.0f} %",
                     "Abschnitte mit Reserve": sum(1 for x in r["alloc"] if x > 0), "Reserve je Abschnitt (min)": " ".join(f"{x / C.UNITS_PER_MIN:.1f}" for x in r["alloc"])})
st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
st.caption("Jede Reserve wird an 6000 frischen Tagen bewertet, die das Optimum nicht gesehen hat; mit denselben Zufallszahlen für alle Verfahren. Die Reserve ist in Zehntelminuten verteilt, Summe = Budget.")

st.markdown("**Die Reserve je Abschnitt**")
st.plotly_chart(build_allocation_bars(run), width="stretch", key=f"alloc_{settings}")
st.caption("Unter jedem Abschnitt steht seine planmäßige Fahrzeit und, wo es einen gibt, das Wort Engpass (kein Zugfolge-Spielraum). Bei Störungslagen ist das gefährdete Fenster rot hinterlegt.")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Wo sammelt sich Verspätung an?**")
    st.plotly_chart(build_delay_profile(run), width="stretch", key=f"profile_{settings}")
with c2:
    st.markdown("**Verspätung und Pünktlichkeit je Verfahren**")
    st.plotly_chart(build_method_bars(run), width="stretch", key=f"methods_{settings}")

view = st.radio("Reserveplan für den PDF-Export", C.VIEW_OPTIONS, key="view_select", horizontal=True, format_func=lambda k: C.METHOD_LABELS[k],
                help="Reine Anzeigewahl: welches Verfahren in den PDF-Plan kommt (keine Einstellung der Rechnung).")
summary_lines = [f"{cfg['n']} Abschnitte, {run['B'] / C.UNITS_PER_MIN:.1f} min Reserve, {settings['trains']} Züge, Wertung: {C.SCORE_LABELS[settings['score']]}",
                 f"Verfahren: {C.METHOD_LABELS[view]}, mittlere Verspätung {results[view]['delay']:.2f} min, {100 * results[view]['punct']:.0f} % pünktlich (frische Tage)."]
st.download_button("📄 Reserveplan als PDF herunterladen", data=generate_plan_pdf(cfg, results[view]["alloc"], "Reserveplan", summary_lines), file_name="reserveplan.pdf", mime="application/pdf",
                   key="pdf_download")

# ------------------------------------------------------------------ Kernabschnitt: Messreihe
st.markdown("---")
st.subheader("📐 Was die Messreihe zeigt")
variants = R.all_variants(res)
byname = {v["name"]: v for v in variants}
std = byname["Standard"]
st.caption(f"Vorgerechnet (tools/sweep.py): {std['n']} Strecken je Variante, Bewertung an frischen Tagen, Mittel ± Standardfehler über die Strecken; Praxisregel, risikoproportionale Regel und Optimum.")
d1, d2, d3, d4 = st.columns(4)
d1.metric("Praxisregel über Optimum", f"{std['over_prop']:.0f} ± {std['over_prop_se']:.0f} %", help="Standardfall, 5 % Budget, 5 Züge: Mittel der Verspätung gegen das Optimum (Basis = Optimum).")
d2.metric("Risikoproportional über Optimum", f"{std['over_risk']:.0f} ± {std['over_risk_se']:.0f} %")
d3.metric("Optimum senkt Verspätung um", f"{std['gain_saa']:.0f} ± {std['gain_saa_se']:.0f} %", help="Gegenüber der Praxisregel.")
d4.metric("Abschnitte ohne Reserve (Optimum)", f"{100 * std['zero_share']:.0f} %", help="Bei freier Verteilung lässt das Optimum die meisten Abschnitte ohne Reserve; mit Mindestanteil nicht.")

st.markdown("**Wie viel das Optimum bringt, hängt am Budget**")
budget_rows = [byname[n] for n in ("Budget 1 %", "Budget 3 %", "Standard", "Budget 7 %", "Budget 10 %")]
st.plotly_chart(build_budget_curve(budget_rows), width="stretch", key="sweep_budget")
st.markdown("**Der Buckel: wo das Optimum die Reserve hinlegt**")
st.plotly_chart(build_mean_allocation(res, "Standard"), width="stretch", key="sweep_alloc")
st.caption(f"Mittlerer Anteil am Budget je Abschnittsposition über {std['n']} Strecken: Im ersten und in den letzten Abschnitten steht fast nichts, der Schwerpunkt der Reserve liegt bei {100 * std['centroid_saa']:.0f} % der Strecke "
           f"(Praxisregel: {100 * std['centroid_prop']:.0f} %). „Alles am Anfang“ oder „alles am Ende“ wäre keine gute Verteilung, solange alle Halte zählen; zählt nur die Endankunft, gehört die Reserve ans Ende.")
st.markdown("**Alle Varianten**")
st.plotly_chart(build_variant_bars(variants), width="stretch", key="sweep_variants")
st.markdown("**Planungstage: Vorsprung und Selbsttäuschung**")
data_rows = [byname[n] for n in ("25 Planungsszenarien", "50 Planungsszenarien", "100 Planungsszenarien", "Standard", "400 Planungsszenarien")]
st.plotly_chart(build_data_curve(data_rows), width="stretch", key="sweep_data")
st.caption("Je weniger Tage das Optimum sieht, desto besser wirkt es auf diesen Tagen und desto weniger davon hält an frischen Tagen (rote Kurve: um wie viel die Planung besser aussieht als die Wirklichkeit).")
st.dataframe(pd.DataFrame([{"Variante": v["name"], "Praxisregel über Opt.": f"{v['over_prop']:.1f} ± {v['over_prop_se']:.1f} %", "risikoprop. über Opt.": f"{v['over_risk']:.1f} ± {v['over_risk_se']:.1f} %",
                            "Optimum senkt um": f"{v['gain_saa']:.1f} ± {v['gain_saa_se']:.1f} %", "pünktlich Opt.": f"{v['punct_saa']:.0f} %", "pünktlich Praxisregel": f"{v['punct_prop']:.0f} %",
                            "Schwerpunkt Opt.": f"{100 * v['centroid_saa']:.0f} %"} for v in variants]), width="stretch", hide_index=True)
if vname:
    cur = byname[vname]
    st.caption(f"Die gewählten Einstellungen entsprechen der Messreihen-Variante „{vname}“: Das Optimum senkt die Verspätung gegenüber der Praxisregel im Mittel um {cur['gain_saa']:.1f} %.")
else:
    st.caption("Für diese Kombination der Regler gibt es keine Messreihen-Variante; die Tabelle zeigt die gemessenen Fälle.")

# ------------------------------------------------------------------ Methodenvergleich
st.markdown("---")
with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich", expanded=False):
    tabs = st.tabs(["📏 Verfahren", "🧮 Optimum (lineares Programm)", "📈 Messreihe"])

    with tabs[0]:
        st.markdown(
            "**Praxisregel:** Jeder Abschnitt bekommt Reserve im Verhältnis seiner planmäßigen Fahrzeit (der übliche Prozentzuschlag), auf Zehntelminuten gerundet. "
            "**Risikoproportional:** im Verhältnis zur erwarteten Störung je Abschnitt (Wahrscheinlichkeit mal mittlere Höhe); sie braucht Risikodaten, nutzt aber noch keine Streckenposition. "
            "**Optimum:** Das lineare Programm minimiert die mittlere gewichtete Verspätung über die Planungstage (SAA, Sample-Average-Approximation) und kennt dafür die Verspätungsfortpflanzung bis in die Folgezüge. "
            "Es sieht nur die Planungstage; bewertet wird an frischen Tagen."
        )
        st.dataframe(pd.DataFrame([{"Abschnitt": k + 1, "Fahrzeit (min)": int(cfg["r"][k]), "Störung je Zug (‰)": int(cfg["p"][k]), "mittlere Höhe (min)": cfg["mu"][k] / 10,
                                    "Engpass": "ja" if k in cfg["bott"] else "", **{C.METHOD_LABELS[m]: results[m]["alloc"][k] / C.UNITS_PER_MIN for m in ("prop", "risk", "saa")}} for k in range(cfg["n"])]),
                     width="stretch", hide_index=True)

    with tabs[1]:
        st.caption(f"Dasselbe lineare Programm mit mehr Planungstagen ({C.EXACT_DATA}): Es zeigt, wie sich Optimum und Verteilung stabilisieren, wenn man mehr beobachtete Tage hat. Das LP hat eine Variable je Reserve und eine "
                   "je Tag, Zug und Abschnitt; die max-Beziehungen der Fortpflanzung sind Ungleichungen.")
        key = tuple(sorted(settings.items()))
        if st.button("🧮 Optimum mit mehr Planungstagen lösen", key="exact_button"):
            with st.spinner(f"Löse das lineare Programm über {C.EXACT_DATA} Tage (einige Sekunden) …"):
                w = M.score_weights(settings["score"], cfg["n"])
                plan = M.disturbances(cfg, C.EXACT_DATA, settings["trains"], settings["corr"], C.TRAIN_SEED_OFFSET + 31 + settings["seed"])
                a, obj = S.optimal_reserve(plan, M.gap_vector(cfg, settings["gap"]), run["B"], w, M.floor_vector(cfg, run["B"], settings["share"]))
                test = M.disturbances(cfg, C.TEST_SCENARIOS, settings["trains"], settings["corr"], C.TEST_SEED_OFFSET + settings["seed"])
                ev = M.evaluate(a, test, M.gap_vector(cfg, settings["gap"]), w)
                st.session_state["exact_result"] = {"key": key, "alloc": [int(x) for x in a], "plan": obj, "delay": ev["delay"]}
        ex = st.session_state.get("exact_result")
        if ex and ex["key"] == key:
            e1, e2, e3 = st.columns(3)
            e1.metric(f"Optimum mit {C.EXACT_DATA} Tagen", f"{ex['delay']:.2f} min", delta=f"{100 * (ex['delay'] / results['saa']['delay'] - 1):+.1f} % gegen das Optimum mit {settings['data']} Tagen", delta_color="inverse")
            e2.metric("Planungstage versprechen", f"{ex['plan']:.2f} min")
            e3.metric("Reserveverschiebung", f"{sum(abs(x - y) for x, y in zip(ex['alloc'], results['saa']['alloc'])) / C.UNITS_PER_MIN:.1f} min", help="Summe der Minuten, um die sich die Verteilung gegenüber dem Optimum mit den gewählten Planungstagen ändert.")
            st.caption("Reserve je Abschnitt (min): " + " ".join(f"{x / C.UNITS_PER_MIN:.1f}" for x in ex["alloc"]) + " (gewählte Planungstage: " + " ".join(f"{x / C.UNITS_PER_MIN:.1f}" for x in results["saa"]["alloc"]) + ")")
        elif ex:
            st.caption("Die Einstellungen haben sich seit dem letzten Lauf geändert - bitte erneut lösen.")

    with tabs[2]:
        st.caption("Alle Varianten der Messreihe: mittlere Verspätung je Verfahren (min, frische Tage) und Anteil pünktlicher Ankünfte.")
        st.dataframe(pd.DataFrame([{"Variante": v["name"], "ohne Reserve": round(v["delay_none"], 2), "Praxisregel": round(v["delay_prop"], 2), "risikoprop.": round(v["delay_risk"], 2),
                                    "Optimum": round(v["delay_saa"], 2), **({"Opt. ohne Störungslagen": round(v["delay_saa_blind"], 2)} if "delay_saa_blind" in v else {}),
                                    "Budget (min)": round(v["B"], 1), "Selbsttäuschung": f"{v['optimism']:.0f} %"} for v in variants]), width="stretch", hide_index=True)

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        f"""
**Strecke.** {C.N_SECTIONS} Abschnitte (Fahrt plus Halt) mit zufälliger Fahrzeit von {C.RUN_MIN} bis {C.RUN_MAX} min; die Strecke wird durch den Seed bestimmt. Mehrere Züge fahren nacheinander; zwei Abschnitte sind Engpässe ohne
Zugfolge-Spielraum.

**Störungen.** Je Zug und Abschnitt tritt mit einer Wahrscheinlichkeit von {C.P_MIN / 10:.0f} bis {(C.P_MIN + C.P_SPAN - 1) / 10:.0f} % eine Störung auf, deren Höhe geometrisch verteilt ist (Mittel {C.MU_TENTHS_MIN / 10:.1f} bis {(C.MU_TENTHS_MIN + C.MU_TENTHS_SPAN - 1) / 10:.1f} min).
Die Reserve eines Abschnitts nimmt Verspätung auf; was bleibt, wird in den nächsten Abschnitt und, über die Zugfolge, an den Folgezug weitergegeben. Bei einer **Störungslage** sind an einem Teil der Tage {C.SHOCK_WINDOW} benachbarte
Abschnitte für alle Züge dieses Tages dreimal so störanfällig.

**Wertung.** Gemessen wird die mittlere Verspätung an allen Abschnittsenden aller Züge, je nach Einstellung gleich gewichtet, nur am Ziel oder mit der Streckenmitte schwerer. Pünktlich heißt höchstens {C.PUNKT} min.

**Optimum.** Aus den Planungstagen entsteht ein lineares Programm; seine Lösung ist die beste Reserve für diese Tage. An {C.TEST_SCENARIOS} frischen Tagen wird jede Reserve neu bewertet, damit das Optimum nicht an seinen Planungstagen
gemessen wird.

**Grenzen.** Synthetische Strecken, gleiche Reserve für alle Züge, keine Überholungen, Wenden oder Dispositionseingriffe, Störungen je Zug unabhängig (außer in der Störungslage). Die Zahlen zeigen Größenordnungen auf diesen Strecken, keine
Fahrplanempfehlung.
"""
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Fortpflanzung.** Zug $j$, Abschnitt $k$: $A_{jk} = \max\left(0,\; A_{j,k-1} + e_{jk} - a_k,\; A_{j-1,k} - g_k\right)$ mit der Störung $e_{jk}$, der Reserve $a_k$ und dem Zugfolge-Spielraum $g_k$ (an den Engpässen 0).

**Optimum (SAA).** Für $S$ Planungstage $s$: $\min \; \frac{1}{S M \sum_k w_k} \sum_{s,j,k} w_k A^s_{jk}$ unter $A^s_{jk} \ge A^s_{j,k-1} + e^s_{jk} - a_k$, $A^s_{jk} \ge A^s_{j-1,k} - g_k$, $A^s_{jk} \ge 0$, $\sum_k a_k = B$, $a_k \ge \ell_k$.
Das Maximum affiner Funktionen ist konvex, das Programm liefert also das echte Minimum über alle Reserven für diese Tage; in Zehntelminuten gerechnet ist die Ecke in der Regel ganzzahlig.

**Praxisregel.** $a_k \propto r_k$ (Fahrzeit), **risikoproportional** $a_k \propto p_k \mu_k$; beide mit Mindestreserve $\ell_k$ und auf Zehntelminuten gerundet (größter Rest).
"""
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Schienenverkehr optimieren](https://sebastianhanisch.net/schienenverkehr-optimierung.html)."
)
