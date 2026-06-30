
import logging
import sys
from scripts.typestrain_finder import find_best_assembly
from scripts.typestrain_download import download_assembly
from scripts.typestrain_report_download import get_type_strain_keys, load_report , log_path, output_dir


def setup_logging(path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(path), logging.StreamHandler(sys.stdout)],
    )


def main():
    species_list = [s.strip() for s in sys.argv[1:] if s.strip()]
    setup_logging(log_path(species_list[0]))
    log = logging.getLogger(__name__)
    outdir = output_dir(species_list[0])
    df = load_report()
    for species in species_list:
        keys = get_type_strain_keys(df, species)
        if keys is None:
            continue

        best = find_best_assembly(species, keys)
        if best is None:
            log.error("%s: no complete genome typestrain assembly found.", species)
            continue
        best["typestrain_accession"]= str(best["typestrain_accession"]).replace("[","").replace("]","").replace("'","")
        log.info("%s: %s (%s, %s, typestrain_key: %s)", species, best["accession"],
                  best["assembly_level"], best["release_date"] , best["typestrain_accession"] )
        download_assembly(best["accession"], outdir)


if __name__ == "__main__":
    main()