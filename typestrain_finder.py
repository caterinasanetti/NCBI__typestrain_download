import json
import logging
import subprocess
import sys

import pandas as pd
from typestrain_report_download import norm

log = logging.getLogger(__name__)
BIOSAMPLE_FIELDS = {"strain", "isolate", "culture_collection"}
def fetch_assembly_summaries(species: str) -> list[dict]:
    """Run `datasets summary genome taxon <species>` and return the
    parsed JSON-lines records, or exit with an error if the command fails."""
    try:
        r = subprocess.run(
            ["datasets", "summary", "genome", "taxon", species, "--as-json-lines"],
            capture_output=True, text=True, timeout= 360,
        )
    except FileNotFoundError:
        log.error("datasets CLI not found. Install from https://www.ncbi.nlm.nih.gov/datasets/docs/v2/")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        log.error("datasets timed out.")
        sys.exit(1)

    if r.returncode != 0:
        log.error("datasets failed: %s", r.stderr.strip())
        sys.exit(1)

    records = []
    for line in r.stdout.splitlines():
        try:
            records.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            continue
    return records


def find_best_assembly(species: str, keys: list[str]) -> dict | None:
    """Among assemblies whose biosample attributes match one of
    `keys`, return the most recent complete-genome assembly,
    preferring RefSeq (GCF_) accessions on ties. Returns None if no
    matching complete-genome assembly exists."""
    norm_keys = {norm(d) for d in keys if norm(d)}
    summaries = fetch_assembly_summaries(species)

    records = []
    for assembly in summaries:
        asm = assembly.get("assembly_info", {})
        attrs = asm.get("biosample", {}).get("attributes", [])
        cands = {
            norm(a["value"]) for a in attrs
            if a.get("name") in BIOSAMPLE_FIELDS and a.get("value")


        }
        if cands & norm_keys:
            release_date = asm.get("release_date", "")
            records.append({
                "accession": assembly.get("accession", ""),
                "assembly_level": asm.get("assembly_level", "Unknown"),
                "release_date": release_date[:10] if release_date else "unknown",
                "typestrain_accession": list(cands & norm_keys)
            })

    if not records:
        return None

    df = pd.DataFrame(records)
    df["sort_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    df["is_gcf"] = df["accession"].str.startswith("GCF_")
    #save to csv and send to the log for info
    log.info("Selected assemblies found for %s:\n%s", species, df.to_csv(index=False))

    final_df_for_species = df[df["assembly_level"] == "Complete Genome"]
    if final_df_for_species.empty:
        return None
    
    typestrain_final = final_df_for_species.sort_values(["sort_date", "is_gcf"], ascending=False).iloc[0].to_dict()
    return typestrain_final