# Nagi

Persönlicher Telegram-Begleiter, betrieben über [Hermes](https://hermes.nousresearch.com) mit einem
lokalen LLM (Qwen3.6-35B-A3B via LM Studio, OpenAI-kompatibel auf `http://localhost:1234/v1`).
Nagi meldet sich morgens und abends, führt einen Wochenrückblick und pflegt ein
Gedächtnis aus einfachen Markdown-Dateien.

## Datenschutz-Architektur (nicht verhandelbar)

Zwei streng getrennte Arten von Dateien:

| Art | Beispiele | Ort |
|---|---|---|
| **Code & Konfig** | `src/`, `nagi_system_prompt.md`, `config/settings.example.toml` | Git / GitHub |
| **Persönliche Daten** | `daten/` (Tage, Wochen, Ziele, Profil), `config/settings.toml` | **nur lokal**, git-ignoriert |

Die `.gitignore` schließt `daten/` und `config/settings.toml` vollständig aus.
Vor jedem Commit gilt: `git check-ignore daten config/settings.toml` muss beide Pfade melden.

## Struktur

```
nagi/
├── nagi_system_prompt.md     # Nagis Persona & Routinen-Logik (→ Symlink von Hermes' SOUL.md)
├── config/
│   ├── settings.example.toml # Vorlage mit Platzhaltern (committet)
│   └── settings.toml         # echte Werte (git-ignoriert)
├── src/
│   ├── memory.py             # liest/schreibt die lokalen Markdown-Dateien
│   ├── context_builder.py    # baut den schlanken Kontext für die Hermes-Cron-Jobs
│   ├── jobs.py               # legt die Hermes-Cron-Jobs idempotent an (Setup, kein Daemon)
│   └── backup.py             # nächtliches rsync-Backup nach scarecrow
├── templates/
│   └── tagesdatei.md         # Vorlage/Beispiel für eine Tagesdatei
└── daten/                    # GIT-IGNORIERT — nur lokal
    ├── tage/                 # 2026-07-22.md — eine Datei pro Tag
    ├── wochen/               # 2026-W30.md — Wochenrückblicke
    ├── ziele.md              # aktueller Stand der Ziele
    └── profil.md             # Nagis längerfristige Beobachtungen
```

## Datenformat

Reine Markdown-Dateien, menschenlesbar, bewusst ohne Datenbank. Jede Tagesdatei
(`daten/tage/YYYY-MM-DD.md`) beginnt mit einem YAML-Frontmatter (`datum`, `typ`)
und hat drei feste Abschnitte:

```markdown
---
datum: 2026-07-22
typ: tag
---

## Morgen
(Antworten aus der Morgen-Routine)

## Abend
(Rückblick aus der Abend-Routine)

## Nagis Notizen
(interne Beobachtungen, die Nagi sich merken will)
```

Klare Header + Frontmatter pro Eintrag, damit eine spätere Migration
(z. B. nach pgvector) ein einfacher Parser-Job bleibt.

## Wie Nagi läuft

- **Hermes-Profil `nagi`** (`~/.hermes/profiles/nagi/`): bewusst schlanke Config
  (nur LM Studio + Telegram + Datei-Zugriff). Der System-Prompt ist
  `nagi_system_prompt.md` aus diesem Repo — per Symlink als `SOUL.md` des Profils eingebunden.
- **Telegram-Token** liegt ausschließlich in `config/settings.toml` (lokal) und in
  `~/.hermes/profiles/nagi/.env` — nie im Code, nie in Git.
- **Zeitgesteuerte Jobs** laufen als native Hermes-Crons im nagi-Profil
  (kein eigener Scheduler-Daemon). `src/jobs.py` legt sie idempotent an:
  - **Morgens** (Default 07:00): Morgen-Routine. `context_builder.py` liefert per
    `--script` den Kontext (letzte Tage, Woche, Ziele, Profil) in den Prompt.
  - **Abends** (Default 22:00): Abend-Routine (Rückblick + dänische Zeile).
  - **Sonntags** (Default 20:00): ausführlicher Wochenrückblick → `daten/wochen/`.
  - **Nachts** (Default 03:00): Backup (`--no-agent`; meldet sich per Telegram nur bei Fehlern).
- **Gedächtnis**: Nach Gesprächen schreibt Nagi selbst (Datei-Toolset) in die
  Tagesdatei; die Logik dafür steckt im System-Prompt.

## Backup

`src/backup.py` packt `daten/` als datiertes Archiv und überträgt es per
rsync/SSH nach scarecrow (`/home/dremet/nagi-backup/`, Rotation konfigurierbar).
**Achtung:** Auf ausdrücklichen Wunsch derzeit **unverschlüsselt** — die Dateien
liegen im Klartext auf dem Server. Verschlüsselung (age) kann später über
`settings.toml` ergänzt werden. Fehler werden geloggt und per Telegram gemeldet
(leise nur bei Erfolg).

## Fahrplan

- [x] **Stufe 0** – Hermes-Profil + Telegram-Bot einrichten
- [x] **Stufe 1** – Datenablage, Gedächtnis-Code, Cron-Jobs, Backup (dieses Repo)
- [ ] **Stufe 2** – Mail-Versand (Wochenrückblick als Mail), Kalender-Anbindung
- [ ] **Stufe 3** – Dashboard
