from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import DataLoader
from tqdm import tqdm

from backend.core.ml.features import AudioPreprocessConfig, LogMelFeatureExtractor
from backend.core.ml.model import AmbientCNN
from ml.dataset import CachedFeatureDataset, UrbanSoundDataset, load_metadata, make_splits
from ml.train import TEST_FOLDS, TRAIN_FOLDS, VAL_FOLDS


@torch.inference_mode()
def collect_predictions(model, loader, device):
    model.eval()
    y_true = []
    y_pred = []
    for features, labels in tqdm(loader, leave=False, desc="test"):
        logits = model(features.to(device))
        y_true.extend(labels.tolist())
        y_pred.extend(logits.argmax(dim=1).cpu().tolist())
    return y_true, y_pred


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", default="data/UrbanSound8K")
    parser.add_argument("--checkpoint", default="backend/core/ml/models/ambient_cnn.pt")
    parser.add_argument("--output", default="ml/artifacts/evaluation_report.json")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--feature-cache-dir", default=None)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
    class_to_idx = checkpoint["class_to_idx"]
    idx_to_class = {idx: name for name, idx in class_to_idx.items()}
    labels = [idx_to_class[i] for i in range(len(idx_to_class))]
    preprocess_config = AudioPreprocessConfig.from_dict(checkpoint["preprocess_config"])
    extractor = LogMelFeatureExtractor(preprocess_config)

    metadata = load_metadata(Path(args.dataset_dir))
    train_rows, val_rows, test_rows = make_splits(metadata, TRAIN_FOLDS, VAL_FOLDS, TEST_FOLDS)
    if args.feature_cache_dir:
        test_dataset = CachedFeatureDataset(test_rows, Path(args.feature_cache_dir))
    else:
        test_dataset = UrbanSoundDataset(test_rows, extractor, augment=False)
    test_loader = DataLoader(
        test_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )

    model = AmbientCNN(num_classes=len(class_to_idx)).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    y_true, y_pred = collect_predictions(model, test_loader, device)
    accuracy = sum(int(a == b) for a, b in zip(y_true, y_pred)) / len(y_true)
    matrix = confusion_matrix(y_true, y_pred, labels=list(range(len(labels))))
    per_class = classification_report(
        y_true,
        y_pred,
        labels=list(range(len(labels))),
        target_names=labels,
        output_dict=True,
        zero_division=0,
    )
    report = {
        "checkpoint": str(args.checkpoint),
        "device": str(device),
        "train_folds": TRAIN_FOLDS,
        "validation_folds": VAL_FOLDS,
        "test_folds": TEST_FOLDS,
        "train_samples": len(train_rows),
        "validation_samples": len(val_rows),
        "test_samples": len(test_rows),
        "best_validation_accuracy": checkpoint["best_val_accuracy"],
        "test_accuracy": accuracy,
        "classes": labels,
        "confusion_matrix": matrix.tolist(),
        "per_class": per_class,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
