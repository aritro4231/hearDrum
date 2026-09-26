from __future__ import annotations

import argparse
from pathlib import Path

from ml.dataset import download_urbansound8k, load_metadata, validate_metadata, write_dataset_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data")
    args = parser.parse_args()

    dataset_dir = download_urbansound8k(Path(args.data_dir))
    metadata = load_metadata(dataset_dir)
    report = validate_metadata(metadata)
    report["source"] = "Zenodo DOI 10.5281/zenodo.1203745"
    report["dataset_dir"] = str(dataset_dir)
    write_dataset_report(Path("ml") / "artifacts" / "dataset_report.json", report)
    print(report)


if __name__ == "__main__":
    main()
