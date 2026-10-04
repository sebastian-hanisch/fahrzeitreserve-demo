"""Feste Annahmen, Regler-Stufen, Presets und Farben der Fahrzeitreserve-Demo (eine Wahrheitsquelle)."""

# ------------------------------------------------------------------ Strecke und Störungen (feste Annahmen)
N_SECTIONS = 12             # Abschnitte der Strecke (Fahrt + Halt)
UNITS_PER_MIN = 10          # Reserven werden in Zehntelminuten (0,1 min) verteilt; Störungen und Fahrzeiten sind ganze Minuten
RUN_MIN, RUN_MAX = 4, 16    # planmäßige Fahrzeit je Abschnitt (min, ganzzahlig, gleichverteilt)
P_MIN, P_SPAN = 30, 91      # Störungswahrscheinlichkeit je Zug und Abschnitt: 30 bis 120 Promille
MU_TENTHS_MIN, MU_TENTHS_SPAN = 18, 25   # mittlere Höhe einer Störung 1,8 bis 4,2 min (Zehntelminuten)
N_BOTTLENECKS = 2           # Abschnitte ohne Zugfolge-Spielraum (jede Verspätung des Vorderzugs wird weitergegeben)
CAP = 60                    # Störungen werden bei 60 min gekappt
PUNKT = 3                   # pünktlich: höchstens 3 min Verspätung
SHOCK_WINDOW = 4            # Störungslage: so viele benachbarte Abschnitte sind betroffen
SHOCK_FACTOR = 3            # dort ist die Störungswahrscheinlichkeit dreimal so hoch (höchstens 600 Promille)
EXACT_DATA = 1000           # Planungstage im Exakt-Tab
TEST_SCENARIOS = 6000       # frische Szenarien, an denen jede Reserve bewertet wird
TEST_SEED_OFFSET = 777000
TRAIN_SEED_OFFSET = 1000

# ------------------------------------------------------------------ Regler
BUDGET_MIN, BUDGET_MAX = 1, 10      # Reservebudget in Prozent der gesamten Fahrzeit
DEFAULT_BUDGET = 5
TRAINS_OPTIONS = (1, 3, 5, 8)
DEFAULT_TRAINS = 5
GAP_OPTIONS = (1, 2, 4)             # Zugfolge-Spielraum (min) an den übrigen Abschnittsenden
DEFAULT_GAP = 2
SCORE_OPTIONS = ("alle", "ende", "last")
SCORE_LABELS = {"alle": "alle Halte gleich", "ende": "nur die Endankunft", "last": "Fahrgastlast (Mitte schwerer)"}
DEFAULT_SCORE = "alle"
SHARE_OPTIONS = (0, 50, 75)         # Mindestanteil je Abschnitt in Prozent des proportionalen Anteils
DEFAULT_SHARE = 0
CORR_OPTIONS = ("aus", "selten", "haeufig")
CORR_LABELS = {"aus": "keine (Störungen unabhängig)", "selten": "selten (10 % der Tage)", "haeufig": "häufig (30 % der Tage)"}
CORR_PERMILLE = {"aus": 0, "selten": 100, "haeufig": 300}
DEFAULT_CORR = "aus"
DATA_OPTIONS = (25, 50, 100, 200, 400)   # Planungsszenarien (beobachtete Tage), nach denen das Optimum rechnet
DEFAULT_DATA = 200
SEED_MIN, SEED_MAX = 0, 9999
DEFAULT_SEED = 500

# ------------------------------------------------------------------ Verfahren
METHODS = ("prop", "risk", "saa")
METHOD_LABELS = {"prop": "Praxisregel (proportional zur Fahrzeit)", "risk": "Risikoproportional", "saa": "Optimum (kennt die Verteilung)",
                 "saa_blind": "Optimum ohne Störungslagen"}
METHOD_COLORS = {"prop": "#7d8898", "risk": "#c77700", "saa": "#2a6fb0", "saa_blind": "#8e44ad"}
VIEW_OPTIONS = ("prop", "risk", "saa")
DEFAULT_VIEW = "saa"

# ------------------------------------------------------------------ Messreihe
RESULTS_FILE = "data/rsv_results.json"
SWEEP_SEEDS = range(100, 140)       # 40 Strecken je Variante
SWEEP_VARIANTS = (          # Name -> (Budget %, Züge, Zugfolge-Spielraum, Wertung, Mindestanteil %, Störungslagen, Planungsszenarien)
    ("Standard", 5, 5, 2, "alle", 0, "aus", 200),
    ("Budget 1 %", 1, 5, 2, "alle", 0, "aus", 200),
    ("Budget 3 %", 3, 5, 2, "alle", 0, "aus", 200),
    ("Budget 7 %", 7, 5, 2, "alle", 0, "aus", 200),
    ("Budget 10 %", 10, 5, 2, "alle", 0, "aus", 200),
    ("1 Zug", 5, 1, 2, "alle", 0, "aus", 200),
    ("8 Züge", 5, 8, 2, "alle", 0, "aus", 200),
    ("Spielraum 1 min", 5, 5, 1, "alle", 0, "aus", 200),
    ("Spielraum 4 min", 5, 5, 4, "alle", 0, "aus", 200),
    ("Wertung Endankunft", 5, 5, 2, "ende", 0, "aus", 200),
    ("Wertung Fahrgastlast", 5, 5, 2, "last", 0, "aus", 200),
    ("Mindestanteil 50 %", 5, 5, 2, "alle", 50, "aus", 200),
    ("Mindestanteil 75 %", 5, 5, 2, "alle", 75, "aus", 200),
    ("Störungslagen selten", 5, 5, 2, "alle", 0, "selten", 200),
    ("Störungslagen häufig", 5, 5, 2, "alle", 0, "haeufig", 200),
    ("25 Planungsszenarien", 5, 5, 2, "alle", 0, "aus", 25),
    ("50 Planungsszenarien", 5, 5, 2, "alle", 0, "aus", 50),
    ("100 Planungsszenarien", 5, 5, 2, "alle", 0, "aus", 100),
    ("400 Planungsszenarien", 5, 5, 2, "alle", 0, "aus", 400),
)
SWEEP_REPS = {"Standard": 5, "25 Planungsszenarien": 5, "50 Planungsszenarien": 5, "100 Planungsszenarien": 5, "400 Planungsszenarien": 5}   # Planungsmengen je Strecke (Mittel), sonst 1
REP_SEED_STEP = 100003

# ------------------------------------------------------------------ Presets (Seeds liegen außerhalb der Messreihen-Seeds)
PRESET_ORDER = ["Standard", "Nur Endankunft", "Mindestanteil", "Störungslagen", "Wenig Daten", "Knappes Budget"]
PRESETS = {
    "Standard": {"budget": 5, "trains": 5, "gap": 2, "score": "alle", "share": 0, "corr": "aus", "data": 200, "seed": 500},
    "Nur Endankunft": {"budget": 5, "trains": 5, "gap": 2, "score": "ende", "share": 0, "corr": "aus", "data": 200, "seed": 500},
    "Mindestanteil": {"budget": 5, "trains": 5, "gap": 2, "score": "alle", "share": 75, "corr": "aus", "data": 200, "seed": 500},
    "Störungslagen": {"budget": 5, "trains": 5, "gap": 2, "score": "alle", "share": 0, "corr": "haeufig", "data": 200, "seed": 500},
    "Wenig Daten": {"budget": 5, "trains": 5, "gap": 2, "score": "alle", "share": 0, "corr": "aus", "data": 25, "seed": 500},
    "Knappes Budget": {"budget": 1, "trains": 5, "gap": 2, "score": "alle", "share": 0, "corr": "aus", "data": 200, "seed": 500},
}
PRESET_HELP = {
    "Standard": "5 Züge, 12 Abschnitte, 5 % der Fahrzeit als Reserve: der Grundfall.",
    "Nur Endankunft": "Es zählt nur die Verspätung am Ziel: Dann gehört die Reserve ans Ende, und die Praxisregel liegt weit daneben.",
    "Mindestanteil": "Kein Abschnitt darf weniger als 75 % seines proportionalen Anteils bekommen: Der Vorsprung des Optimums schrumpft.",
    "Störungslagen": "An 30 % der Tage sind vier benachbarte Abschnitte für alle Züge dreimal so störanfällig: Das Optimum verschiebt die Reserve dorthin.",
    "Wenig Daten": "Nur 25 beobachtete Tage als Planungsgrundlage: Das Optimum passt sich dem Zufall der wenigen Tage an.",
    "Knappes Budget": "Nur 1 % der Fahrzeit als Reserve: Es gibt wenig zu verteilen, der Unterschied ist klein.",
}


def fmt_min(x, digits=1):
    return f"{x:.{digits}f} min"
