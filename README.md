# Fahrzeitreserve: Wo setzt man den Puffer? (Streamlit-Demo)

**[→ Demo live ausprobieren](https://sebastianhanisch-fahrzeitreserve-demo.streamlit.app/)**

Interaktive **Fall-Demo** zur Verteilung von Fahrzeitreserven im Portfolio von [Sebastian Hanisch](https://sebastianhanisch.net) (Operations Research und Machine Learning).
**Fünfter Baustein der Reihe Bahn/Schienenverkehr** nach dem [Taktfahrplan](https://github.com/sebastian-hanisch/taktfahrplan-demo) und dem [Trassenkonflikt](https://github.com/sebastian-hanisch/trassenkonflikt-demo),
in denen Fahrzeitreserven bewusst offen blieben.

Auf einer Strecke mit zwölf Abschnitten fahren mehrere Züge hintereinander und werden zufällig gestört. Im Fahrplan darf ein **festes Budget an Reserve** (Prozent der Fahrzeit, in Zehntelminuten) auf die Abschnitte
verteilt werden; jede Reserve nimmt Verspätung auf, die sich sonst entlang der Strecke und auf die Folgezüge überträgt. Die Demo vergleicht die **Praxisregel** (proportional zur Fahrzeit), eine
**risikoproportionale Regel** und das **Optimum nach Planungstagen** (lineares Programm, Sample-Average-Approximation) und fragt, **wie viel die Praxisregel verschenkt** und **wie sehr die Antwort davon abhängt, wo Verspätung gezählt wird**.

## Kernfrage

Wo gehört die Reserve hin, wenn man nur ein festes Budget verteilen darf? Verwandt, aber eine andere Frage: [bullwhip-demo](https://github.com/sebastian-hanisch/bullwhip-demo) zeigt, dass sich Schwankung entlang einer
Kette verstärkt; [robuste-kaiplatz-demo](https://github.com/sebastian-hanisch/robuste-kaiplatz-demo) stellt einen Gesamtpuffer gegen Neuplanung. Hier ist die Entscheidung die **Allokation** eines Budgets entlang einer Kette,
gemessen gegen die Praxisregel. Das Ergebnis ist qualitativ kein Neuland der Forschung (aus der Fließband-Literatur ist die „storage bowl“-Aussage bekannt, dass Puffer in der Mitte statt gleichmäßig stehen sollen;
Literatur dazu und zu Fahrzeitzuschlägen: Kroon u. a., Transportation Research Part B 42(6), 2008; Goverde, Transportation Research Part B 41(2), 2007), aber im Portfolio neu.

## Befunde und Korrekturen gegenüber dem Plan

- **Der Vorab-Befund hielt nicht ganz.** Die Vorab-Messreihe (Agent, kontinuierliche Reserven, andere Störungsverteilung) fand die Praxisregel **20,5 %** über dem Optimum; in dieser Fassung (ganzzahliger SplitMix64-Generator,
  Reserve in Zehntelminuten, 200 Planungstage, andere Störungsverteilung) sind es **15,9 ± 0,8 %**. Die Größenordnung und die Form (Optimum ist ein Buckel) blieben, der Betrag nicht; die README-Zahlen sind die neuen.
- **Ein Fehler der ersten Fassung:** Mit Reserve in ganzen Minuten blieb der Mindestanteil wirkungslos (identische Zahlen wie ohne), weil bei 6 Minuten Budget auf 12 Abschnitte die Untergrenzen auf null abgerundet
  wurden. Die Messreihe zeigte es als Spalte mit lauter gleichen Zahlen; die Reserve wird jetzt in Zehntelminuten verteilt.
- **Zusatzmodellierung gegenüber dem Plan:** Die Wertung (wo zählt Verspätung?), gemeinsame **Störungslagen** (an einem Teil der Tage sind vier benachbarte Abschnitte für alle Züge dreimal so störanfällig) und die
  **Zahl der Planungstage** sind Regler. Die Störungslagen verändern die optimale Verteilung, aber wer sie nicht kennt, verliert dabei fast nichts (siehe Tabelle): ein Negativbefund, der stehen bleibt.
- Port 8970.

## Modell

- **Strecke:** 12 Abschnitte (Fahrt plus Halt), planmäßige Fahrzeit 4 bis 16 min je Abschnitt (zufällig, durch den Seed bestimmt). Mehrere Züge (1 bis 8) fahren nacheinander; zwei Abschnitte sind Engpässe ohne Zugfolge-Spielraum,
  an den übrigen Abschnittsenden beträgt er 1, 2 oder 4 min.
- **Störungen:** je Zug und Abschnitt mit 3 bis 12 % Wahrscheinlichkeit, Höhe geometrisch verteilt (Mittel 1,8 bis 4,2 min), gekappt bei 60 min. Alles ganzzahlig mit **SplitMix64** (`rsv_rng.py`), Zufallszahlen für
  Planungstage und frische Tage unabhängig. **Störungslage:** an 10 % bzw. 30 % der Tage ist die Wahrscheinlichkeit in vier benachbarten Abschnitten für alle Züge dreimal so hoch.
- **Fortpflanzung:** `A[j,k] = max(0, A[j,k-1] + e[j,k] - a[k], A[j-1,k] - g[k])` mit Störung `e`, Reserve `a` (für alle Züge gleich) und Zugfolge-Spielraum `g`.
- **Wertung:** mittlere Verspätung an allen Abschnittsenden aller Züge: alle gleich, nur die Endankunft, oder Fahrgastlast (Gewicht min(k+1, n−k), Mitte schwerer). Pünktlich heißt höchstens 3 min.
- **Budget:** 1 bis 10 % der Fahrzeit in Zehntelminuten (auf 0,1 min gerundet); Mindestanteil je Abschnitt 0, 50 oder 75 % seines proportionalen Anteils.

## Methodik

- **Praxisregel** und **risikoproportional** (`rsv_model.method_allocation`): Reserve proportional zur Fahrzeit bzw. zu Störungswahrscheinlichkeit mal mittlerer Höhe, oberhalb der Mindestreserve, auf Zehntelminuten gerundet
  (größter Rest).
- **Optimum** (`rsv_saa.py`): lineares Programm über S Planungstage (SAA), Epigraphformulierung der max-Beziehungen, HiGHS. Das Problem ist konvex (Maximum affiner Funktionen), das LP also das echte Minimum über alle Reserven
  für diese Tage; die Ecke ist in Zehntelminuten ganzzahlig (sonst ein MILP). **Bewertet wird jede Reserve an 6000 frischen Tagen**, die das Optimum nicht gesehen hat, mit denselben Zufallszahlen für alle Verfahren.
- **Optimum ohne Störungslagen:** dasselbe LP, geplant nach Tagen ohne Störungslage, bewertet an Tagen mit Störungslage.
- **Vorgerechnete Messreihe** (`tools/sweep.py` → `data/rsv_results.json`, rund 3,5 Minuten parallel): 19 Varianten mit je 40 Strecken (Seeds 100–139). Der Standardfall und die Planungstage-Reihe (25, 50, 100, 400) mitteln je
  Strecke über 5 Planungsmengen. Live läuft das Optimum für die gewählte Strecke; der Exakt-Tab löst es mit 1000 Planungstagen.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen stehen in `tests/test_claims.py`. 40 Strecken je Variante (Seeds 100–139), Mittel ± Standardfehler über die Strecken, bewertet an frischen Tagen; **Verspätung über dem Optimum** (Basis = Optimum) bzw.
„Optimum senkt um“ (Basis = Praxisregel).

| Frage | Befund |
|---|---|
| Wie viel verschenkt die Praxisregel? (5 % Budget, 5 Züge) | Sie liegt **15.9 ± 0.8 %** über dem Optimum (risikoproportional **14.5 ± 0.7 %**); das Optimum senkt die Verspätung um **13.6 ± 0.6 %**. |
| Hängt das am Budget? | Das Optimum senkt die Verspätung bei 1 / 3 / 5 / 7 / 10 % Budget um **5.1 / 10.6 / 13.6 / 15.2 / 16.5 %**. |
| Wo liegt die Reserve? | Das Optimum lässt im Mittel **59 %** der Abschnitte ohne Reserve; sein Schwerpunkt liegt bei **43 %** der Strecke (Praxisregel 48 %): ein Buckel in der Mitte, im ersten und in den letzten Abschnitten fast nichts. |
| Zählt nur die Endankunft? | Dann liegt die Praxisregel **56.0 ± 2.7 %** über dem Optimum, das seine Reserve ans Ende legt (Schwerpunkt **99 %**); bei Fahrgastlast **29.5 ± 1.1 %**. Die Platzierung folgt der Wertung. |
| Und ein Mindestanteil je Abschnitt? | Das Optimum senkt die Verspätung dann nur noch um **9.7 ± 0.4 %** (Mindestanteil 50 %) bzw. **6.9 ± 0.3 %** (75 %). |
| Gemeinsame Störungslagen? | Das Optimum legt **56 %** (selten) bzw. **63 %** (häufig) der Reserve in das gefährdete Fenster, die Praxisregel **33 %**. Wer sie nicht kennt, verliert nur **0.1 %** bzw. **0.8 %**. |
| Wie viele Planungstage braucht das Optimum? | Bei 25 / 50 / 100 / 400 Tagen senkt es die Verspätung um **11.4 / 12.6 / 13.3 / 13.8 %**; die Planung sieht bei 25 Tagen um **4.8 ± 1.8 %** besser aus als die Wirklichkeit, bei 400 Tagen um **0.8 ± 0.5 %**. |
| Zugzahl und Spielraum? | Mit 1 Zug senkt das Optimum die Verspätung um **11.1 %**, mit 8 Zügen um **14.8 %**; bei 1 min Spielraum um **12.3 %**, bei 4 min um **15.2 %**. |

## Ehrliche Grenzen

- **Die Platzierung folgt der Wertung.** Zählt nur die Endankunft, gehört die Reserve ans Ende; zählen alle Halte gleich, in die Mitte. Es gibt keine Verteilung, die für jede Wertung stimmt.
- **Freie Verteilung ist unrealistisch:** Das Optimum lässt 59 % der Abschnitte ohne Reserve. Mit Mindestanteil schrumpft sein Vorsprung auf 7 bis 10 %.
- Das Optimum kennt die Störungsverteilung (aus den Planungstagen); in der Praxis hat man nur Schätzungen. Die Planungstage-Reihe zeigt, wie sich das auswirkt.
- Synthetische Strecken: gleiche Reserve für alle Züge, keine Überholungen, Wenden oder Dispositionseingriffe, Störungen je Zug unabhängig (außer in der Störungslage), keine Echtdaten.
- Die Messreihe hat 40 Strecken je Variante; Unterschiede von wenigen Zehnteln Prozent zwischen Varianten sind vom Rauschen nicht zu trennen. Das Verspätungsniveau (rund 70 % pünktlich ohne Reserve) ist hoch gewählt.

## Tests

Siehe `tests/`: Strecke und Fortpflanzung von Hand gerechnet und gegen eine naive Dreifachschleife, **LP gegen eine Vollaufzählung aller ganzzahligen Reserven** (`tests/test_saa.py`, auch mit Mindestreserve und
Wertungen), Störungslage als Kopplung derselben Tage, Meldungen an ihren Schwellen mit künstlichen Zahlen, Statistik an einer von Hand gerechneten Mini-Ergebnisdatei, Preset-Kriterien (jedes Kriterium kippt einzeln),
`test_claims.py` (jede README-Zahl gegen die Ergebnisdatei), AppTest-Rauchtests (Voreinstellung, jedes Preset, Randwerte, Permalink, Exakt-Tab). Keine Wall-Clock-Assertions.
`tools/mutation_check.py` baut einzelne Fehler in die Module ein und prüft, ob die Tests sie finden.

```
python -m pytest tests -q
```

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `rsv_constants.py` | feste Annahmen, Regler-Stufen, Presets, Messreihen-Varianten |
| `rsv_rng.py`, `rsv_model.py` | SplitMix64; Strecke, Störungen, Fortpflanzung, Faustregeln |
| `rsv_saa.py` | LP der Sample-Average-Approximation (Optimum) |
| `rsv_evaluation.py` | Live-Rechnung, Bewertung an frischen Tagen, Meldungen |
| `rsv_results.py`, `rsv_stories.py`, `rsv_presets.py` | Auswertung der Messreihe; Preset-Kriterien; Permalink und Presets |
| `rsv_visualization.py`, `rsv_pdf_export.py` | Plotly-Figuren; Reserveplan als PDF |
| `data/rsv_results.json` | Ergebnisse der Messreihe |
| `tools/` | `sweep.py`, `preset_search.py`, `mutation_check.py`, `PRESET_SWEEP.md` |

## Bewusst nicht umgesetzt

Reserven je Zug, Überholungen und Wenden, Dispositionseingriffe und Wartezeitregeln, Fahrgastumlegung mit echten Anschlüssen, Echtdaten, Optimierung der Zugfolge selbst, andere Zielgrößen als die mittlere Verspätung
(Pünktlichkeit als Ziel wird gemessen, nicht optimiert).

## Lokal ausführen

```
pip install -r requirements.txt
streamlit run app.py
```

Die Messreihe neu erzeugen: `python tools/sweep.py`.

Gebaut mit Streamlit, Plotly, SciPy, pandas und fpdf2.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zum Thema: [Schienenverkehr optimieren](https://sebastianhanisch.net/schienenverkehr-optimierung.html).
