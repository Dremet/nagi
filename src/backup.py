"""Nächtliches Backup von daten/ nach scarecrow (rsync über SSH).

ACHTUNG: auf ausdrücklichen Wunsch (Juli 2026) derzeit UNVERSCHLÜSSELT —
die Archive liegen im Klartext auf dem Server. Für eine spätere Umstellung
auf age: in settings.toml verschluesselung = "age" vorgesehen (noch nicht
implementiert; der Schlüssel müsste lokal bleiben, nie auf den Server).

Läuft als Hermes-Cron mit --no-agent: leerer stdout = Erfolg = keine
Telegram-Nachricht; jede Ausgabe wird André zugestellt. Deshalb schreibt
dieses Skript NUR bei Fehlern (oder Warnungen) auf stdout. Jeder Lauf
landet zusätzlich im Log (logs/backup.log).
"""

from __future__ import annotations

import datetime as dt
import subprocess
import sys
import tempfile
from pathlib import Path

import memory

REPO = Path(__file__).resolve().parent.parent
LOG = REPO / "logs" / "backup.log"

SSH_OPTS = ["-o", "ConnectTimeout=15", "-o", "BatchMode=yes"]


def log(text: str) -> None:
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {text}\n")


def lauf(cmd: list[str]) -> None:
    """Kommando ausführen; bei Fehlschlag Exception mit stderr-Auszug."""
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:2])} → Exit {r.returncode}: {r.stderr.strip()[-400:]}")


def backup() -> str:
    cfg = memory.lade_settings()["backup"]
    ziel = f"{cfg['user']}@{cfg['host']}"
    zielpfad = cfg["zielpfad"].rstrip("/")
    daten = memory.daten_dir()

    if not daten.is_dir() or not any(daten.rglob("*.md")):
        raise RuntimeError(f"Datenverzeichnis {daten} fehlt oder ist leer — nichts gesichert!")

    stempel = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    name = f"nagi-daten-{stempel}.tar.gz"

    with tempfile.TemporaryDirectory() as tmp:
        archiv = Path(tmp) / name
        # -C ins Elternverzeichnis, damit im Archiv nur "daten/..." steht
        lauf(["tar", "-czf", str(archiv), "-C", str(daten.parent), daten.name])
        lauf(["ssh", *SSH_OPTS, ziel, f"mkdir -p {zielpfad}"])
        lauf(["rsync", "-e", f"ssh {' '.join(SSH_OPTS)}", str(archiv), f"{ziel}:{zielpfad}/"])

    # Rotation: nur die neuesten N Archive auf dem Server behalten
    behalten = int(cfg.get("rotation", 14))
    r = subprocess.run(
        ["ssh", *SSH_OPTS, ziel, f"ls -1 {zielpfad}/nagi-daten-*.tar.gz 2>/dev/null"],
        capture_output=True, text=True, timeout=60,
    )
    archive = sorted(z for z in r.stdout.split() if z.strip())
    for alt in archive[:-behalten] if len(archive) > behalten else []:
        lauf(["ssh", *SSH_OPTS, ziel, f"rm -f {alt}"])

    return f"{name} → {ziel}:{zielpfad}/ ({len(archive)} Archive auf dem Server)"


def main() -> int:
    try:
        ergebnis = backup()
        log(f"OK  {ergebnis}")
        return 0  # stdout bleibt leer → keine Telegram-Nachricht
    except Exception as e:  # noqa: BLE001 — bewusst alles fangen: Backup darf nie still scheitern
        log(f"FEHLER  {e}")
        print(f"⚠️ Nagi-Backup fehlgeschlagen: {e}\nDetails: {LOG}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
