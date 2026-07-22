"""Nagis Gedächtnis: liest und schreibt die lokalen Markdown-Dateien in daten/.

Bewusst simpel: reine Textdateien mit Frontmatter und festen Abschnitten,
kein DB-Zwang. Eine spätere Migration (z. B. pgvector) muss nur diese eine
Datei ersetzen. Alle Pfade kommen aus config/settings.toml ([pfade].daten).
"""

from __future__ import annotations

import datetime as dt
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Die drei festen Abschnitte jeder Tagesdatei (siehe templates/tagesdatei.md)
ABSCHNITTE = ("Morgen", "Abend", "Nagis Notizen")


def lade_settings() -> dict:
    """settings.toml laden; fehlt sie, dient settings.example.toml als Fallback."""
    for name in ("settings.toml", "settings.example.toml"):
        pfad = REPO / "config" / name
        if pfad.exists():
            return tomllib.loads(pfad.read_text(encoding="utf-8"))
    raise FileNotFoundError("Weder settings.toml noch settings.example.toml gefunden.")


def daten_dir() -> Path:
    return Path(lade_settings()["pfade"]["daten"]).expanduser()


# ── Tagesdateien ────────────────────────────────────────────────────────


def tagesdatei(datum: dt.date | None = None) -> Path:
    datum = datum or dt.date.today()
    return daten_dir() / "tage" / f"{datum.isoformat()}.md"


def lege_tagesdatei_an(datum: dt.date | None = None) -> Path:
    """Tagesdatei aus der Vorlage anlegen, falls sie noch nicht existiert."""
    datum = datum or dt.date.today()
    pfad = tagesdatei(datum)
    if not pfad.exists():
        pfad.parent.mkdir(parents=True, exist_ok=True)
        vorlage = (REPO / "templates" / "tagesdatei.md").read_text(encoding="utf-8")
        pfad.write_text(vorlage.replace("{{datum}}", datum.isoformat()), encoding="utf-8")
    return pfad


def ergaenze_abschnitt(abschnitt: str, text: str, datum: dt.date | None = None) -> Path:
    """Text ans Ende eines der festen Abschnitte der Tagesdatei anhängen."""
    if abschnitt not in ABSCHNITTE:
        raise ValueError(f"Unbekannter Abschnitt {abschnitt!r}, erlaubt: {ABSCHNITTE}")
    pfad = lege_tagesdatei_an(datum)
    zeilen = pfad.read_text(encoding="utf-8").splitlines()

    # Einfügepunkt: direkt vor der nächsten "## "-Überschrift nach dem Abschnitt
    # (bzw. am Dateiende, wenn der Abschnitt der letzte ist).
    start = zeilen.index(f"## {abschnitt}")
    ende = len(zeilen)
    for i in range(start + 1, len(zeilen)):
        if zeilen[i].startswith("## "):
            ende = i
            break
    while ende > start + 1 and zeilen[ende - 1].strip() == "":
        ende -= 1  # Leerzeilen am Abschnittsende nicht anhäufen

    zeilen[ende:ende] = [text.rstrip(), ""]
    pfad.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return pfad


def lese_letzte_tage(n: int = 6) -> list[tuple[str, str]]:
    """Die letzten n vorhandenen Tagesdateien als (Datum, Inhalt), älteste zuerst."""
    ordner = daten_dir() / "tage"
    if not ordner.is_dir():
        return []
    dateien = sorted(ordner.glob("????-??-??.md"))[-n:]
    return [(p.stem, p.read_text(encoding="utf-8")) for p in dateien]


# ── Wochen, Ziele, Profil ───────────────────────────────────────────────


def wochendatei(datum: dt.date | None = None) -> Path:
    datum = datum or dt.date.today()
    jahr, woche, _ = datum.isocalendar()
    return daten_dir() / "wochen" / f"{jahr}-W{woche:02d}.md"


def lese_aktuelle_woche() -> str:
    """Inhalt des Wochenrückblicks der aktuellen ISO-Woche ('' falls keiner da)."""
    return _lese_optional(wochendatei())


def lese_letzte_woche() -> str:
    return _lese_optional(wochendatei(dt.date.today() - dt.timedelta(days=7)))


def lese_letzte_wochen(n: int = 4) -> list[tuple[str, str]]:
    """Die letzten n vorhandenen Wochenrückblicke als (Name, Inhalt), älteste zuerst."""
    ordner = daten_dir() / "wochen"
    if not ordner.is_dir():
        return []
    dateien = sorted(ordner.glob("????-W??.md"))[-n:]
    return [(p.stem, p.read_text(encoding="utf-8")) for p in dateien]


def lese_ziele() -> str:
    return _lese_optional(daten_dir() / "ziele.md")


def lese_profil() -> str:
    return _lese_optional(daten_dir() / "profil.md")


def _lese_optional(pfad: Path) -> str:
    return pfad.read_text(encoding="utf-8") if pfad.exists() else ""
