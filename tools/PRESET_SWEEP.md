# Preset-Abstimmung (tools/preset_search.py)

Seeds 500..539, außerhalb der Messreihen-Seeds (100-139). Alle Presets zeigen dieselbe Strecke (gleicher Seed); ein Seed besteht, wenn alle Kriterien aller Presets gelten (`rsv_stories.py`).

Bestanden: 11 von 40 Seeds: [500, 501, 502, 510, 514, 529, 530, 531, 533, 534, 536]

- Standard: durchgefallen je Kriterium gain 3x, few_sections 3x, interior 0x, sweep_gain 0x, sweep_zero 0x
- Nur Endankunft: durchgefallen je Kriterium end 3x, rule_far 1x, more_than_standard 0x, sweep_over 0x, sweep_centroid 0x
- Mindestanteil: durchgefallen je Kriterium floor 0x, smaller_gain 0x, still_positive 0x, sweep_small 0x
- Störungslagen: durchgefallen je Kriterium window 18x, window_more 18x, blind_exists 0x, sweep_small_loss 0x, sweep_window 0x
- Wenig Daten: durchgefallen je Kriterium few 0x, warning 19x, sweep_optimism 0x, sweep_less 0x
- Knappes Budget: durchgefallen je Kriterium small_gain 0x, small 3x, sweep_small 0x, budget_small 0x

Gewählt: Seed 500.
