from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader
from tqdm import tqdm

from backend.core.ml.features import AudioPreprocessConfig, LogMelFeatureExtractor
from backend.core.ml.model import AmbientCNN
from ml.dataset import CLASS_NAMES, CachedFeatureDataset, UrbanSoundDataset, load_metadata, make_splits, validate_metadata


TRAIN_FOLDS = [1, 2, 3, 4, 5, 6, 7, 8]
VAL_FOLDS = [9]
TEST_FOLDS = [10]


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def run_epoch(model, loader, criterion, device, optimizer=None):
    is_train = optimizer is not None
    model.train(is_train)
    total_loss = 0.0
    correct = 0
    total = 0
    for features, labels in tqdm(loader, leave=False, desc="train" if is_train else "eval"):
        features = features.to(device)
        labels = labels.to(device)
        if is_train:
            optimizer.zero_grad(set_to_none=True)
        logits = model(features)
        loss = criterion(logits, labels)
        if is_train:
            loss.backward()
            optimizer.step()
        batch_size = labels.size(0)
        total_loss += loss.item() * batch_size
        correct += (logits.argmax(dim=1) == labels).sum().item()
        total += batch_size
    return total_loss / total, correct / total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", default="data/UrbanSound8K")
    parser.add_argument("--checkpoint", default="backend/core/ml/models/ambient_cnn.pt")
    parser.add_argument("--artifacts-dir", default="ml/artifacts")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--feature-cache-dir", default=None)
    args = parser.parse_args()

    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    artifacts_dir = Path(args.artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    metadata = load_metadata(Path(args.dataset_dir))
    dataset_report = validate_metadata(metadata)
    train_rows, val_rows, test_rows = make_splits(metadata, TRAIN_FOLDS, VAL_FOLDS, TEST_FOLDS)
    preprocess_config = AudioPreprocessConfig()
    extractor = LogMelFeatureExtractor(preprocess_config)

    if args.feature_cache_dir:
        train_dataset = CachedFeatureDataset(train_rows, Path(args.feature_cache_dir))
        val_dataset = CachedFeatureDataset(val_rows, Path(args.feature_cache_dir))
    else:
        train_dataset = UrbanSoundDataset(train_rows, extractor, augment=True)
        val_dataset = UrbanSoundDataset(val_rows, extractor, augment=False)

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )

    model = AmbientCNN(num_classes=len(CLASS_NAMES)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=3)

    history = []
    best_val_acc = -1.0
    checkpoint_path = Path(args.checkpoint)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        train_loss, train_acc = run_epoch(model, train_loader, criterion, device, optimizer)
        val_loss, val_acc = run_epoch(model, val_loader, criterion, device)
        scheduler.step(val_acc)
        row = {
            "epoch": epoch,
            "train_loss": train_loss,
            "train_accuracy": train_acc,
            "val_loss": val_loss,
            "val_accuracy": val_acc,
            "learning_rate": optimizer.param_groups[0]["lr"],
        }
        history.append(row)
        print(
            f"epoch={epoch:03d} train_loss={train_loss:.4f} train_acc={train_acc:.4f} "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}"
        )
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "class_to_idx": {name: idx for idx, name in enumerate(CLASS_NAMES)},
                    "preprocess_config": preprocess_config.to_dict(),
                    "architecture": "AmbientCNN",
                    "best_val_accuracy": best_val_acc,
                    "epoch": epoch,
                    "train_folds": TRAIN_FOLDS,
                    "validation_folds": VAL_FOLDS,
                    "test_folds": TEST_FOLDS,
                    "train_samples": len(train_rows),
                    "validation_samples": len(val_rows),
                    "test_samples": len(test_rows),
                    "dataset_report": dataset_report,
                    "hyperparameters": vars(args),
                },
                checkpoint_path,
            )

    training_report = {
        "device": str(device),
        "epochs_completed": args.epochs,
        "best_validation_accuracy": best_val_acc,
        "train_folds": TRAIN_FOLDS,
        "validation_folds": VAL_FOLDS,
        "test_folds": TEST_FOLDS,
        "train_samples": len(train_rows),
        "validation_samples": len(val_rows),
        "test_samples": len(test_rows),
        "preprocess_config": preprocess_config.to_dict(),
        "input_tensor_dimensions": [1, preprocess_config.n_mels, preprocess_config.expected_frames],
        "history": history,
    }
    (artifacts_dir / "training_report.json").write_text(json.dumps(training_report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
