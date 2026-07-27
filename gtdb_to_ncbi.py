#!/usr/bin/env python3
import gzip
import logging
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import cast

import pandas as pd

log = logging.getLogger(__name__)

METADATA_BAC_URL = (
    "https://data.gtdb.ecogenomic.org/releases/release226/226.0/"
    "bac120_metadata_r226.tsv.gz"
)


def metadata_path(date: datetime | None = None) -> Path:
    """Local filename for the (date-stamped) GTDB bacterial metadata."""
    date = date or datetime.now()
    return Path(f"bac120_metadata_{date.strftime('%Y%m%d')}.tsv")


def download_metadata(path: Path) -> None:
    """Download the GTDB bacterial metadata (gzipped TSV) if not already
    present, decompress it to `path`, and remove any older dated copies
    left over from previous runs."""
    if path.exists():
        log.debug("Metadata file %s already exists. Skipping download.", path.name)
        return
    
    log.info("Downloading GTDB metadata from %s", METADATA_BAC_URL)
    gz_path = path.with_suffix(path.suffix + ".gz")
    urllib.request.urlretrieve(METADATA_BAC_URL, gz_path)
    
    with gzip.open(gz_path, "rt") as src, path.open("wt") as dst:
        dst.write(src.read())
    
    gz_path.unlink()
    
    for old in Path(".").glob("bac120_metadata_*.tsv"):
        if old != path:
            log.info("Removing old metadata file: %s", old.name)
            old.unlink()


def load_metadata() -> dict[str, str]:
    """Download (if needed) and load the GTDB bacterial metadata,
    returning a mapping of GTDB species name -> NCBI organism name."""
    path = metadata_path()
    download_metadata(path)
    
    log.info("Loading GTDB-to-NCBI mapping from %s", path.name)
    df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
    
    df["gtdb_species"] = df["gtdb_taxonomy"].str.extract(r"s__([^;]+)$")
    
    raw_mapping = (
        df[["gtdb_species", "ncbi_organism_name"]]
        .replace("", pd.NA)
        .dropna()
        .drop_duplicates(subset="gtdb_species")
        .set_index("gtdb_species")["ncbi_organism_name"]
        .to_dict()
    )  
    
    return cast(dict[str, str], raw_mapping)


if __name__ == "__main__":
    # Example usage for testing the script independently
    logging.basicConfig(level=logging.INFO)
    mapping = load_metadata()
    print(f"Loaded {len(mapping)} GTDB-to-NCBI species mappings.")