
import csv
import logging
import sys
from pathlib import Path
from typestrain_finder import find_best_assembly
from typestrain_download import download_assembly
from typestrain_report_download import get_type_strain_keys, load_report , log_path, output_dir
from gtdb_to_ncbi import load_metadata


def setup_logging(path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(path), logging.StreamHandler(sys.stdout)],
    )


def append_summary_tsv(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["Sample", "species", "ncbi_species", "status", "accession", "assembly_level", "release_date", "typestrain_key"]
    write_header = not path.exists()
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def main():
    args = [s.strip() for s in sys.argv[1:] if s.strip()]
    if len(args) < 2:
        raise SystemExit("Usage: python main.py <sample_name> <species ...>")

    sample_name = args[0]
    output_name = args[1]
    species_list = args[1:]

    setup_logging(log_path(output_name))
    log = logging.getLogger(__name__)
    outdir = output_dir(output_name)
    summary_tsv = outdir / "type_strain_assemblies.tsv"
    df = load_report()
    gtdb_to_ncbi = None
    for species in species_list:
        keys, status = get_type_strain_keys(df, species)
        ncbi_species = species
        if keys is None and status == "not_found": 
            if gtdb_to_ncbi is None:
                gtdb_to_ncbi = load_metadata()
            mapped = gtdb_to_ncbi.get(species)
            if mapped and mapped != species:
                log.info("%s: not found in type-strain report, mapped to NCBI species %s", species, mapped)
                ncbi_species = mapped
                keys, status = get_type_strain_keys(df, ncbi_species)
                if keys is not None:
                    ncbi_species = mapped
        if keys is None:
            if status == "not_found":
                append_summary_tsv(
                    summary_tsv,
                    {
                        "Sample": sample_name,
                        "species": species,
                        "ncbi_species": ncbi_species,
                        "status": status,
                        "accession": "",
                        "assembly_level": "",
                        "release_date": "",
                        "typestrain_key": "",
                    },
                )
            continue

        best = find_best_assembly(ncbi_species, keys)
        if best is None:
            log.error("%s: no complete genome typestrain assembly found.", species)
            continue
        best["typestrain_accession"]= str(best["typestrain_accession"]).replace("[","").replace("]","").replace("'","")
        log.info("%s: %s (%s, %s, typestrain_key: %s)", species, best["accession"],
                  best["assembly_level"], best["release_date"] , best["typestrain_accession"] )
        append_summary_tsv(
            summary_tsv,
            {
                "Sample": sample_name,
                "species": species,
                "ncbi_species": ncbi_species,
                "status": "selected",
                "accession": best["accession"],
                "assembly_level": best["assembly_level"],
                "release_date": best["release_date"],
                "typestrain_key": best["typestrain_accession"],
            },
        )
        download_assembly(best["accession"], outdir)


if __name__ == "__main__":
    main()