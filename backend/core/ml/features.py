from __future__ import annotations

import io
from dataclasses import asdict, dataclass
from pathlib import Path

import torch
import torchaudio
import soundfile as sf
from scipy.io import wavfile


@dataclass(frozen=True)
class AudioPreprocessConfig:
    sample_rate: int = 22050
    duration_seconds: float = 4.0
    n_fft: int = 1024
    hop_length: int = 512
    n_mels: int = 64
    f_min: float = 20.0
    f_max: float | None = None
    top_db: float = 80.0

    @property
    def num_samples(self) -> int:
        return int(self.sample_rate * self.duration_seconds)

    @property
    def expected_frames(self) -> int:
        return 1 + self.num_samples // self.hop_length

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, values: dict | None) -> "AudioPreprocessConfig":
        return cls(**(values or {}))


def _samples_to_waveform(samples) -> torch.Tensor:
    if hasattr(samples, "copy"):
        samples = samples.copy()
    waveform = torch.as_tensor(samples)
    if waveform.ndim == 0:
        raise ValueError("Audio contains no waveform samples.")
    if waveform.ndim == 1:
        waveform = waveform.unsqueeze(0)
    else:
        waveform = waveform.transpose(0, 1)
    if waveform.dtype.is_floating_point:
        waveform = waveform.float()
    else:
        max_value = float(torch.iinfo(waveform.dtype).max)
        waveform = waveform.float() / max_value
    return waveform


def load_audio(path: str | Path) -> tuple[torch.Tensor, int]:
    path = Path(path)
    if path.suffix.lower() == ".wav":
        try:
            sample_rate, samples = wavfile.read(path)
        except ValueError:
            samples, sample_rate = sf.read(path, always_2d=False)
        return _samples_to_waveform(samples), int(sample_rate)
    waveform, sample_rate = torchaudio.load(str(path))
    return waveform, sample_rate


def load_audio_bytes(data: bytes, suffix: str = ".wav") -> tuple[torch.Tensor, int]:
    if not data:
        raise ValueError("Audio upload is empty.")

    buffer = io.BytesIO(data)
    if suffix.lower() == ".wav":
        try:
            sample_rate, samples = wavfile.read(buffer)
        except ValueError:
            buffer.seek(0)
            samples, sample_rate = sf.read(buffer, always_2d=False)
        return _samples_to_waveform(samples), int(sample_rate)

    samples, sample_rate = sf.read(buffer, always_2d=False)
    return _samples_to_waveform(samples), int(sample_rate)


class LogMelFeatureExtractor(torch.nn.Module):
    def __init__(self, config: AudioPreprocessConfig | None = None):
        super().__init__()
        self.config = config or AudioPreprocessConfig()
        self._mel = torchaudio.transforms.MelSpectrogram(
            sample_rate=self.config.sample_rate,
            n_fft=self.config.n_fft,
            hop_length=self.config.hop_length,
            n_mels=self.config.n_mels,
            f_min=self.config.f_min,
            f_max=self.config.f_max,
            power=2.0,
        )
        self._db = torchaudio.transforms.AmplitudeToDB(
            stype="power",
            top_db=self.config.top_db,
        )

    def forward(self, waveform: torch.Tensor, sample_rate: int) -> torch.Tensor:
        return self.extract(waveform, sample_rate)

    def extract(self, waveform: torch.Tensor, sample_rate: int) -> torch.Tensor:
        if waveform.ndim == 1:
            waveform = waveform.unsqueeze(0)
        if waveform.ndim != 2:
            raise ValueError("Expected waveform shaped [channels, samples] or [samples].")

        waveform = waveform.float()
        waveform = waveform.mean(dim=0, keepdim=True)

        if sample_rate != self.config.sample_rate:
            waveform = torchaudio.functional.resample(
                waveform,
                orig_freq=sample_rate,
                new_freq=self.config.sample_rate,
            )

        waveform = self._fit_duration(waveform)
        peak = waveform.abs().max()
        if peak > 0:
            waveform = waveform / peak

        features = self._db(self._mel(waveform))
        mean = features.mean()
        std = features.std().clamp_min(1e-6)
        features = (features - mean) / std
        return features

    def _fit_duration(self, waveform: torch.Tensor) -> torch.Tensor:
        target = self.config.num_samples
        samples = waveform.shape[-1]
        if samples > target:
            return waveform[..., :target]
        if samples < target:
            return torch.nn.functional.pad(waveform, (0, target - samples))
        return waveform
