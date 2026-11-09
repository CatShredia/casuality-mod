"""Zip the exported mod folder into no_commit/mod_zips/<date>_<sha>_<subject>.zip."""
import re, subprocess, sys, zipfile
from datetime import datetime
from pathlib import Path

MOD = Path("C:/Users/catsh/CatshrediasDocs/Paradox Interactive/Hearts of Iron IV/mod/Ktits")
REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "no_commit" / "mod_zips"

def git(*a):
    return subprocess.check_output(["git", "-C", str(REPO), *a], text=True, encoding="utf-8").strip()

sha = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
short = git("rev-parse", "--short", sha)
subject = git("log", "-1", "--format=%s", sha)
slug = re.sub(r"[^A-Za-z0-9]+", "-", subject).strip("-")[:60]
name = f"{datetime.now():%Y-%m-%d_%H%M}_{short}_{slug}.zip"
if not MOD.is_dir():
    sys.exit(f"mod folder not found: {MOD}")
OUT.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(OUT / name, "w", zipfile.ZIP_DEFLATED) as z:
    for f in MOD.rglob("*"):
        if f.is_file():
            z.write(f, Path("Ktits") / f.relative_to(MOD))
print("mod zip:", OUT / name)
