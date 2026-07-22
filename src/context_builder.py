"""Baut den Kontextblock, der Nagis Cron-Jobs vorangestellt wird.

Hermes-Cron ruft dieses Skript per --script auf (über einen kleinen Wrapper,
den jobs.py generiert): der stdout landet vor jedem Lauf im Prompt des Jobs.

Bewusst selektiv, damit der Kontext klein bleibt: die letzten Tage wörtlich,
die aktuelle Wochenzusammenfassung, Ziele und Profil — nicht mehr.

Aufruf: python3 context_builder.py {morgen|abend|woche}
"""

from __future__ import annotations

import datetime as dt
import sys

import memory

TAGE_WOERTLICH = 28   # ~4 Wochen wörtlich (Andrés Wunsch, 22.07.2026)
WOCHEN_ANZAHL = 4     # dazu die letzten Wochenrückblicke

WOCHENTAGE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag",
              "Freitag", "Samstag", "Sonntag")


def baue_kontext(modus: str) -> str:
    heute = dt.date.today()
    teile = [
        f"# Kontextblock ({WOCHENTAGE[heute.weekday()]}, {heute:%d.%m.%Y})",
        "Dieser Block wurde automatisch aus Nagis Gedächtnis zusammengestellt.",
    ]

    def block(titel: str, inhalt: str) -> None:
        if inhalt.strip():
            teile.append(f"\n## {titel}\n\n{inhalt.strip()}")

    tage = memory.lese_letzte_tage(TAGE_WOERTLICH)
    if tage:
        teile.append("\n## Letzte Tage")
        for datum, inhalt in tage:
            teile.append(f"\n### {datum}\n\n{inhalt.strip()}")

    wochen = memory.lese_letzte_wochen(WOCHEN_ANZAHL)
    if wochen:
        teile.append("\n## Wochenrückblicke")
        for name, inhalt in wochen:
            teile.append(f"\n### {name}\n\n{inhalt.strip()}")

    block("Ziele (ziele.md)", memory.lese_ziele())
    block("Profil — Nagis Beobachtungen (profil.md)", memory.lese_profil())

    if modus == "woche":
        ziel = memory.wochendatei(heute)
        teile.append(f"\n## Hinweis\n\nZieldatei für den heutigen Wochenrückblick: `{ziel}`")

    return "\n".join(teile) + "\n"


def main() -> int:
    modus = sys.argv[1] if len(sys.argv) > 1 else "morgen"
    if modus not in ("morgen", "abend", "woche"):
        print(f"Unbekannter Modus: {modus}", file=sys.stderr)
        return 2
    print(baue_kontext(modus))
    return 0


if __name__ == "__main__":
    sys.exit(main())
