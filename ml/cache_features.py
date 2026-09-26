from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from tqdm import tqdm

from backend.core.ml.features import AudioPreprocessConfig, LogMelFeatureExtractor, load_audio
from ml.dataset import load_metadata, validate_metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", default="data/UrbanSound8K")
    parser.add_argument("--cache-dir", default="data/urbansound8k_features")
    args = parser.parse_args()

    metadata = load_metadata(Path(args.dataset_dir))
    report = validate_metadata(metadata)
    config = AudioPreprocessConfig()
    extractor = LogMelFeatureExtractor(config)
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    for row in tqdm(metadata.itertuples(index=False), total=len(metadata), desc="Caching log-mels"):
        fold_dir = cache_dir / f"fold{row.fold}"
        fold_dir.mkdir(parents=True, exist_ok=True)
        output_path = fold_dir / f"{Path(row.slice_file_name).stem}.pt"
        if output_path.exists():
            continue
        waveform, sample_rate = load_audio(row.audio_path)
        torch.save(extractor.extract(waveform, sample_rate), output_path)

    cache_report = {
        "dataset_report": report,
        "preprocess_config": config.to_dict(),
        "cache_dir": str(cache_dir),
    }
    (cache_dir / "cache_report.json").write_text(json.dumps(cache_report, indent=2), encoding="utf-8")
    print(json.dumps(cache_report, indent=2))


if __name__ == "__main__":
    main()
