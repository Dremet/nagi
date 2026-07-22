"""Legt Nagis Hermes-Cron-Jobs idempotent an.

Kein eigener Scheduler-Daemon: das profil-eigene Cron-System von Hermes
übernimmt Zeitplan, LLM-Lauf und Telegram-Zustellung. Dieses Skript ist
reines Setup — es generiert kleine Skript-Wrapper im nagi-Profil und
(re-)erzeugt die vier Jobs mit den Zeiten aus settings.toml. Es ist
gefahrlos mehrfach ausführbar: bestehende Jobs gleichen Namens werden
ersetzt.

Aufruf:
    python3 src/jobs.py           # Jobs anlegen/aktualisieren
    python3 src/jobs.py --pause   # alle Nagi-Jobs pausieren
    python3 src/jobs.py --resume  # wieder aktivieren
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import memory

REPO = Path(__file__).resolve().parent.parent
NAGI_CLI = Path.home() / ".local" / "bin" / "nagi"   # Hermes-Wrapper fürs nagi-Profil
PROFIL = Path.home() / ".hermes" / "profiles" / "nagi"
SCRIPTS = PROFIL / "scripts"
JOBS_JSON = PROFIL / "cron" / "jobs.json"

# Prompts bewusst knapp: die eigentliche Routine-Logik steckt im System-Prompt
# (nagi_system_prompt.md), der Kontext kommt aus dem --script-Wrapper.
JOBS = {
    "Nagi Morgen-Routine": {
        "zeit_key": "morgens",
        "modus": "morgen",
        "prompt": "Auslöser: Morgen-Routine. Folge der Morgen-Routine aus deinem "
                  "System-Prompt und nutze den angehängten Kontextblock. Antworte "
                  "direkt mit der Telegram-Nachricht an André, ohne Meta-Kommentare.",
    },
    "Nagi Abend-Routine": {
        "zeit_key": "abends",
        "modus": "abend",
        "prompt": "Auslöser: Abend-Routine. Folge der Abend-Routine aus deinem "
                  "System-Prompt und nutze den angehängten Kontextblock. Antworte "
                  "direkt mit der Telegram-Nachricht an André, ohne Meta-Kommentare.",
    },
    "Nagi Wochenrückblick": {
        "zeit_key": "woche",
        "modus": "woche",
        "prompt": "Auslöser: Wochenrückblick. Folge dem Wochenrückblick aus deinem "
                  "System-Prompt: Schreibe zuerst die vollständige Wochendatei "
                  "(Zielpfad steht im Kontextblock unter 'Hinweis'), sende dann die "
                  "Kurzfassung als Telegram-Nachricht an André.",
    },
    "Nagi Backup": {
        "zeit_key": "backup",
        "modus": None,  # --no-agent: Skript IST der Job, stdout geht direkt raus
        "prompt": None,
    },
}


def wrapper_schreiben() -> None:
    """Kleine Aufruf-Wrapper ins Profil legen (Hermes erwartet Skripte dort)."""
    SCRIPTS.mkdir(exist_ok=True)
    python = sys.executable  # der Interpreter, mit dem jobs.py gestartet wurde
    ziele = {"nagi_morgen.py": ("context_builder.py", "morgen"),
             "nagi_abend.py": ("context_builder.py", "abend"),
             "nagi_woche.py": ("context_builder.py", "woche"),
             "nagi_backup.py": ("backup.py", None)}
    for name, (skript, arg) in ziele.items():
        cmd = [python, str(REPO / "src" / skript)] + ([arg] if arg else [])
        (SCRIPTS / name).write_text(
            "#!/usr/bin/env python3\n"
            "# Auto-generiert von nagi/src/jobs.py — Änderungen bitte dort.\n"
            "import subprocess, sys\n"
            f"r = subprocess.run({cmd!r}, capture_output=True, text=True)\n"
            "sys.stdout.write(r.stdout)\n"
            "sys.stderr.write(r.stderr)\n"
            "sys.exit(r.returncode)\n",
            encoding="utf-8",
        )


def bestehende_jobs() -> dict[str, str]:
    """Vorhandene Cron-Jobs des Profils als {Name: Job-ID}."""
    if not JOBS_JSON.exists():
        return {}
    daten = json.loads(JOBS_JSON.read_text(encoding="utf-8"))
    jobs = daten if isinstance(daten, list) else daten.get("jobs", [])
    return {j["name"]: j["id"] for j in jobs}


def cron(*args: str) -> str:
    r = subprocess.run([str(NAGI_CLI), "cron", *args], capture_output=True, text=True)
    # Achtung: `hermes cron` liefert auch bei Fehlern Exit 0 — daher Ausgabe prüfen.
    if r.returncode != 0 or "Failed" in r.stdout or "Failed" in r.stderr:
        raise RuntimeError(f"nagi cron {' '.join(args[:2])} → {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout


def anlegen() -> None:
    zeiten = memory.lade_settings()["jobs"]
    wrapper_schreiben()
    vorhanden = bestehende_jobs()
    wrapper = {"morgen": "nagi_morgen.py", "abend": "nagi_abend.py",
               "woche": "nagi_woche.py", None: "nagi_backup.py"}

    for name, job in JOBS.items():
        if name in vorhanden:  # ersetzen statt doppeln
            cron("remove", vorhanden[name])
        args = [str(zeiten[job["zeit_key"]])]
        if job["prompt"]:
            args.append(job["prompt"])
        # --script erwartet NUR den Dateinamen, aufgelöst im scripts/-Ordner des Profils
        args += ["--name", name, "--deliver", "telegram",
                 "--script", wrapper[job["modus"]],
                 "--workdir", str(REPO)]
        if job["modus"] is None:
            args.append("--no-agent")
        cron("create", *args)
        print(f"✓ {name} ({zeiten[job['zeit_key']]})")


def pausieren(resume: bool = False) -> None:
    aktion = "resume" if resume else "pause"
    for name, job_id in bestehende_jobs().items():
        if name in JOBS:
            cron(aktion, job_id)
            print(f"✓ {aktion}: {name}")


def main() -> int:
    if "--pause" in sys.argv:
        pausieren()
    elif "--resume" in sys.argv:
        pausieren(resume=True)
    else:
        anlegen()
    return 0


if __name__ == "__main__":
    sys.exit(main())
