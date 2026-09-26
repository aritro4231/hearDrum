from __future__ import annotations

from pathlib import Path

import torch

from .features import AudioPreprocessConfig, LogMelFeatureExtractor, load_audio
from .model import AmbientCNN


DEFAULT_CHECKPOINT = Path(__file__).resolve().parent / "models" / "ambient_cnn.pt"


class EnvironmentAudioClassifier:
    def __init__(self, checkpoint_path: str | Path = DEFAULT_CHECKPOINT, device: str | None = None):
        self.checkpoint_path = Path(checkpoint_path)
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        checkpoint = torch.load(self.checkpoint_path, map_location=self.device, weights_only=False)
        self.class_to_idx = checkpoint["class_to_idx"]
        self.idx_to_class = {int(v): k for k, v in self.class_to_idx.items()}
        self.preprocess_config = AudioPreprocessConfig.from_dict(checkpoint["preprocess_config"])
        self.extractor = LogMelFeatureExtractor(self.preprocess_config)
        self.model = AmbientCNN(num_classes=len(self.class_to_idx))
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()

    @torch.inference_mode()
    def predict_path(self, audio_path: str | Path) -> dict:
        waveform, sample_rate = load_audio(audio_path)
        return self.predict_waveform(waveform, sample_rate)

    @torch.inference_mode()
    def predict_waveform(self, waveform: torch.Tensor, sample_rate: int) -> dict:
        features = self.extractor.extract(waveform, sample_rate).unsqueeze(0).to(self.device)
        logits = self.model(features)
        probabilities = torch.softmax(logits, dim=1)[0]
        confidence, class_idx = probabilities.max(dim=0)
        return {
            "class": self.idx_to_class[int(class_idx.item())],
            "confidence": float(confidence.item()),
            "probabilities": {
                self.idx_to_class[i]: float(probabilities[i].item())
                for i in range(len(self.idx_to_class))
            },
        }


def predict_environment(audio: str | Path | torch.Tensor, sample_rate: int | None = None) -> dict:
    classifier = EnvironmentAudioClassifier()
    if isinstance(audio, (str, Path)):
        return classifier.predict_path(audio)
    if sample_rate is None:
        raise ValueError("sample_rate is required when passing a waveform tensor.")
    return classifier.predict_waveform(audio, sample_rate)
