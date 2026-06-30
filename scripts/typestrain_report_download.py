import logging
import re
import urllib.request
from pathlib import Path
import pandas as pd
from datetime import datetime
log = logging.getLogger(__name__)

TYPESTRAIN_REPORT_URL = (
    "https://ftp.ncbi.nlm.nih.gov/genomes/ASSEMBLY_REPORTS/"
    "prokaryote_type_strain_report.txt"
)


def report_path(date: datetime | None = None) -> Path:
    """Local filename for the (date-stamped) type-strain report."""
    date = date or datetime.now()
    return Path(f"prokaryote_type_strain_report_{date.strftime('%Y%m%d')}.txt")


def output_dir(first_species: str) -> Path:
    """Directory genome downloads are written to, named after the first
    species requested."""
    return Path(f"{first_species.replace(' ', '_')}_typestrain")


def log_path(first_species: str) -> Path:
    """Log file path, named after the first species requested."""
    return Path(f"get_type_strains_{first_species.replace(' ', '_')}.log")


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def download_report(path: Path) -> None:
    """Download the type-strain report if not already present, and remove
    any older dated copies left over from previous runs."""
    if path.exists():
        return
    urllib.request.urlretrieve(TYPESTRAIN_REPORT_URL, path)
    for old in Path(".").glob("prokaryote_type_strain_report_*.txt"):
        if old != path:
            old.unlink()


def load_report() -> pd.DataFrame:
    """Download (if needed) and load the type-strain report as a
    DataFrame, with normalized column names and a lowercase name column
    for lookups."""
    path = report_path()
    download_report(path)
    df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
    df.columns = df.columns.str.lstrip("#").str.strip()
    df["name_norm"] = df["scientific-name"].str.strip().str.lower()
    return df


def get_type_strain_keys(df: pd.DataFrame, species: str) -> list[str] | None:
    """Look up `species` in the report and return its type-strain
    keys, or None (logging the reason) if the species can't be
    used: not found, no designation on file, or type strain not
    sequenced."""
    rows = df[df["name_norm"] == species.lower()]
    if rows.empty:
        log.error("%s: not found in type-strain report.", species)
        return None
    row = rows.iloc[0]

    raw = row["type-materials-and-coidentical-strains"].strip()
    n_type = int(row["number-of-assemblies-from-type-materials-per-species"].strip() or 0)

    if not raw or raw.upper() == "NULL":
        log.error("%s: no type strain designation.", species)
        return None
    if n_type == 0:
        log.error("%s: type strain not sequenced. Total assemblies: %s",
                   species, row["number-of-assemblies-per-taxon"])
        return None

    keys = [p.strip() for p in re.sub(r"\[\[.*?\]\]", "", raw).split(",") if p.strip()]
    if not keys:
        log.error("%s: could not parse type strain field. Raw: %s", species, raw)
        return None

    return keys