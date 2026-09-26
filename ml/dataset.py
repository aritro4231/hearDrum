from __future__ import annotations

import csv
import hashlib
import json
import random
import tarfile
import time
from pathlib import Path

import pandas as pd
import requests
import torch
from torch.utils.data import Dataset
from tqdm import tqdm

from backend.core.ml.features import LogMelFeatureExtractor, load_audio


DATASET_URL = "https://zenodo.org/record/1203745/files/UrbanSound8K.tar.gz?download=1"
DATASET_MD5 = "9aa69802bbf37fb986f71ec1483a196e"
CLASS_NAMES = [
    "air_conditioner",
    "car_horn",
    "children_playing",
    "dog_bark",
    "drilling",
    "engine_idling",
    "gun_shot",
    "jackhammer",
    "siren",
    "street_music",
]


def resumable_download(url: str, archive_path: Path, retries: int = 8) -> None:
    for attempt in range(1, retries + 1):
        existing = archive_path.stat().st_size if archive_path.exists() else 0
        headers = {"Range": f"bytes={existing}-"} if existing else {}
        try:
            with requests.get(url, headers=headers, stream=True, timeout=60) as response:
                if existing and response.status_code == 200:
                    existing = 0
                response.raise_for_status()
                total = int(response.headers.get("content-length", "0")) + existing
                mode = "ab" if existing else "wb"
                with archive_path.open(mode) as handle, tqdm(
                    total=total,
                    initial=existing,
                    unit="B",
                    unit_scale=True,
                    desc="Downloading",
                ) as progress:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        handle.write(chunk)
                        progress.update(len(chunk))
            return
        except (requests.RequestException, OSError) as exc:
            if attempt == retries:
                raise
            wait_seconds = min(60, 2**attempt)
            print(f"Download interrupted ({exc}); retrying in {wait_seconds}s.")
            time.sleep(wait_seconds)


def download_urbansound8k(data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    archive_path = data_dir / "UrbanSound8K.tar.gz"
    dataset_dir = data_dir / "UrbanSound8K"
    if dataset_dir.exists():
        return dataset_dir
    if not archive_path.exists():
        resumable_download(DATASET_URL, archive_path)
    else:
        resumable_download(DATASET_URL, archive_path)
    md5 = hashlib.md5()
    with archive_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            md5.update(chunk)
    if md5.hexdigest() != DATASET_MD5:
        raise RuntimeError(f"MD5 mismatch for {archive_path}: {md5.hexdigest()}")
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(data_dir)
    return dataset_dir


def load_metadata(dataset_dir: Path) -> pd.DataFrame:
    metadata_path = dataset_dir / "metadata" / "UrbanSound8K.csv"
    rows = []
    with metadata_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            audio_path = dataset_dir / "audio" / f"fold{row['fold']}" / row["slice_file_name"]
            if audio_path.exists():
                rows.append(
                    {
                        "slice_file_name": row["slice_file_name"],
                        "fold": int(row["fold"]),
                        "classID": int(row["classID"]),
                        "class": row["class"],
                        "audio_path": str(audio_path),
                    }
                )
    return pd.DataFrame(rows)


def validate_metadata(metadata: pd.DataFrame) -> dict:
    classes = sorted(metadata["class"].unique().tolist())
    if classes != sorted(CLASS_NAMES):
        raise RuntimeError(f"Unexpected classes: {classes}")
    return {
        "usable_samples": int(len(metadata)),
        "classes": CLASS_NAMES,
        "fold_counts": {str(k): int(v) for k, v in metadata["fold"].value_counts().sort_index().items()},
        "class_counts": {str(k): int(v) for k, v in metadata["class"].value_counts().sort_index().items()},
    }


def make_splits(metadata: pd.DataFrame, train_folds: list[int], val_folds: list[int], test_folds: list[int]):
    train = metadata[metadata["fold"].isin(train_folds)].reset_index(drop=True)
    val = metadata[metadata["fold"].isin(val_folds)].reset_index(drop=True)
    test = metadata[metadata["fold"].isin(test_folds)].reset_index(drop=True)
    return train, val, test


class UrbanSoundDataset(Dataset):
    def __init__(
        self,
        rows: pd.DataFrame,
        extractor: LogMelFeatureExtractor,
        augment: bool = False,
    ):
        self.rows = rows.reset_index(drop=True)
        self.extractor = extractor
        self.augment = augment

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int):
        row = self.rows.iloc[idx]
        waveform, sample_rate = load_audio(row["audio_path"])
        if self.augment:
            waveform = self._augment_waveform(waveform)
        features = self.extractor.extract(waveform, sample_rate)
        return features, int(row["classID"])

    def _augment_waveform(self, waveform: torch.Tensor) -> torch.Tensor:
        if random.random() < 0.5:
            shift = random.randint(-2205, 2205)
            waveform = torch.roll(waveform, shifts=shift, dims=-1)
        if random.random() < 0.35:
            noise = torch.randn_like(waveform) * 0.005
            waveform = waveform + noise
        return waveform


class CachedFeatureDataset(Dataset):
    def __init__(self, rows: pd.DataFrame, cache_dir: Path, preload: bool = True):
        self.rows = rows.reset_index(drop=True)
        self.cache_dir = cache_dir
        self.preloaded = None
        if preload:
            features = []
            labels = []
            for idx in range(len(self.rows)):
                feature, label = self._load_item(idx)
                features.append(feature)
                labels.append(label)
            self.preloaded = (torch.stack(features), torch.tensor(labels, dtype=torch.long))

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int):
        if self.preloaded is not None:
            features, labels = self.preloaded
            return features[idx], labels[idx]
        return self._load_item(idx)

    def _load_item(self, idx: int):
        row = self.rows.iloc[idx]
        cache_path = self.cache_dir / f"fold{row['fold']}" / f"{Path(row['slice_file_name']).stem}.pt"
        features = torch.load(cache_path, map_location="cpu", weights_only=False)
        return features, int(row["classID"])


def write_dataset_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
