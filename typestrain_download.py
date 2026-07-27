import logging
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

log = logging.getLogger(__name__)

def download_assembly(accession: str, outdir: Path) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    zip_path = outdir / f"{accession}.zip"
    fna_genome = outdir / f"{accession}.fna"

    if fna_genome.exists():
        log.info("Already have %s, skipping download", fna_genome.name)
        return fna_genome

    if not zip_path.exists():
        r = subprocess.run(
            ["datasets", "download", "genome", "accession", accession,
             "--include", "genome", "--filename", str(zip_path)],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            log.error("Download failed: %s", r.stderr.strip())
            sys.exit(1)

    with zipfile.ZipFile(zip_path) as zf:
        member = next((n for n in zf.namelist() if n.endswith(".fna")), None)
        if member is None:
            log.error("No .fna found for %s", accession)
            sys.exit(1)
        with zf.open(member) as src, fna_genome.open("wb") as dst:
            shutil.copyfileobj(src, dst)

    return fna_genome
