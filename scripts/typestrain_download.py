import logging
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

def download_assembly(accession: str, outdir: Path) -> None:
    """Download the genome FASTA for `accession` into `outdir` as
    `<accession>.zip` or exits the process on failure"""
    outdir.mkdir(parents=True, exist_ok=True)
    zip_path = outdir / f"{accession}.zip"
    r = subprocess.run(
        ["datasets", "download", "genome", "accession", accession,
         "--include", "genome", "--filename", str(zip_path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        log.error("Download failed: %s", r.stderr.strip())
        sys.exit(1)