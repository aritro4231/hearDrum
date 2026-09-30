from __future__ import annotations

import argparse
import io
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
import wave
from array import array
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

import django  # noqa: E402

django.setup()

import torch  # noqa: E402
from django.conf import settings  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402

from core.ambient import analyze_ambient_recording, decode_uploaded_wav, get_ambient_classifier  # noqa: E402
from core.views import analyze_ambient  # noqa: E402


def make_pcm16_wav(
    *,
    sample_rate: int,
    duration_seconds: float,
    frequency_hz: float = 440.0,
    amplitude: float = 0.25,
) -> bytes:
    sample_count = int(round(sample_rate * duration_seconds))
    frames = array(
        "h",
        (
            int(
                max(-1.0, min(1.0, amplitude * math.sin(2 * math.pi * frequency_hz * i / sample_rate)))
                * 32767
            )
            for i in range(sample_count)
        ),
    )
    if sys.byteorder != "little":
        frames.byteswap()

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(frames.tobytes())
    return buffer.getvalue()


def make_upload(audio_bytes: bytes) -> SimpleUploadedFile:
    return SimpleUploadedFile(
        "ambient-benchmark.wav",
        audio_bytes,
        content_type="audio/wav",
    )


def percentile(values: list[float], percent: float) -> float:
    if not values:
        raise ValueError("Cannot calculate a percentile for an empty sample.")
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = (len(sorted_values) - 1) * (percent / 100.0)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return sorted_values[int(rank)]
    lower_value = sorted_values[lower]
    upper_value = sorted_values[upper]
    return lower_value + (upper_value - lower_value) * (rank - lower)


def summarize(samples_ms: list[float]) -> dict[str, float]:
    return {
        "runs": len(samples_ms),
        "p50_ms": statistics.median(samples_ms),
        "p95_ms": percentile(samples_ms, 95),
        "mean_ms": statistics.fmean(samples_ms),
        "min_ms": min(samples_ms),
        "max_ms": max(samples_ms),
    }


def sync_device(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def time_runs(
    *,
    name: str,
    runs: int,
    measured: Callable[[], object],
    before_timing: Callable[[], None] | None = None,
    after_timing: Callable[[], None] | None = None,
) -> list[float]:
    samples_ms: list[float] = []
    for index in range(runs):
        if before_timing is not None:
            before_timing()
        start_ns = time.perf_counter_ns()
        measured()
        if after_timing is not None:
            after_timing()
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        samples_ms.append(elapsed_ms)
        if runs >= 50 and (index + 1) % 25 == 0:
            print(f"{name}: completed {index + 1}/{runs} runs", flush=True)
    return samples_ms


def get_cpu_name() -> str:
    commands = [
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)",
        ],
        ["wmic", "cpu", "get", "name"],
    ]
    for command in commands:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except Exception:
            continue
        lines = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip() and line.strip().lower() != "name"
        ]
        if lines:
            return lines[0]
    return platform.processor() or "unknown"


def build_request_factory_runner(audio_bytes: bytes) -> Callable[[], object]:
    factory = APIRequestFactory()
    user = User(username="ambient-benchmark")

    def run_view() -> object:
        request = factory.post(
            "/api/ambient/analyze/",
            {"audio": make_upload(audio_bytes)},
            format="multipart",
        )
        force_authenticate(request, user=user)
        response = analyze_ambient(request)
        if response.status_code != 200:
            raise RuntimeError(f"Unexpected response status {response.status_code}: {response.data}")
        response.render()
        return response

    return run_view


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark the hearDrum ambient audio inference pipeline.",
    )
    parser.add_argument("--runs", type=int, default=100, help="Measured runs per benchmark.")
    parser.add_argument("--warmup", type=int, default=10, help="Warmup runs before measurement.")
    parser.add_argument("--sample-rate", type=int, default=48_000, help="Synthetic WAV sample rate.")
    parser.add_argument("--duration", type=float, default=4.0, help="Synthetic WAV duration in seconds.")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "ml" / "artifacts" / "ambient_benchmark.json",
        help="JSON report path.",
    )
    args = parser.parse_args()

    if args.runs < 1:
        raise SystemExit("--runs must be at least 1.")
    if args.warmup < 0:
        raise SystemExit("--warmup must be zero or greater.")

    audio_bytes = make_pcm16_wav(
        sample_rate=args.sample_rate,
        duration_seconds=args.duration,
    )

    print("Loading ambient checkpoint and warming model cache...", flush=True)
    classifier = get_ambient_classifier()
    device = classifier.device

    decoded_waveform, decoded_sample_rate, decoded_duration = decode_uploaded_wav(make_upload(audio_bytes))
    features = classifier.extractor.extract(decoded_waveform, decoded_sample_rate).unsqueeze(0).to(device)

    @torch.inference_mode()
    def run_model_inference() -> tuple[int, float]:
        logits = classifier.model(features)
        probabilities = torch.softmax(logits, dim=1)[0]
        confidence, class_idx = probabilities.max(dim=0)
        return int(class_idx.item()), float(confidence.item())

    def run_preprocess() -> torch.Tensor:
        return classifier.extractor.extract(decoded_waveform, decoded_sample_rate)

    def run_decode() -> tuple[torch.Tensor, int, float]:
        return decode_uploaded_wav(make_upload(audio_bytes))

    def run_decode_preprocess() -> torch.Tensor:
        waveform_tensor, sample_rate, _duration = decode_uploaded_wav(make_upload(audio_bytes))
        return classifier.extractor.extract(waveform_tensor, sample_rate)

    def run_service() -> dict:
        return analyze_ambient_recording(make_upload(audio_bytes))

    run_view = build_request_factory_runner(audio_bytes)

    for _ in range(args.warmup):
        run_decode()
        run_preprocess()
        sync_device(device)
        run_model_inference()
        sync_device(device)
        run_service()
        run_view()

    prediction = run_service()
    print(
        "Warmup complete. "
        f"Prediction={prediction['environment_class']} "
        f"confidence={prediction['confidence']}",
        flush=True,
    )

    timings = {
        "decode_ms": time_runs(
            name="decode_ms",
            runs=args.runs,
            measured=run_decode,
        ),
        "preprocess_ms": time_runs(
            name="preprocess_ms",
            runs=args.runs,
            measured=run_preprocess,
        ),
        "decode_preprocess_ms": time_runs(
            name="decode_preprocess_ms",
            runs=args.runs,
            measured=run_decode_preprocess,
        ),
        "model_inference_ms": time_runs(
            name="model_inference_ms",
            runs=args.runs,
            measured=run_model_inference,
            before_timing=lambda: sync_device(device),
            after_timing=lambda: sync_device(device),
        ),
        "ambient_service_total_ms": time_runs(
            name="ambient_service_total_ms",
            runs=args.runs,
            measured=run_service,
        ),
        "django_view_total_ms": time_runs(
            name="django_view_total_ms",
            runs=args.runs,
            measured=run_view,
        ),
    }

    metrics = {name: summarize(samples) for name, samples in timings.items()}
    metrics["ambient_service_total_ms"]["approx_throughput_per_second"] = (
        args.runs / (sum(timings["ambient_service_total_ms"]) / 1000.0)
    )
    metrics["django_view_total_ms"]["approx_throughput_per_second"] = (
        args.runs / (sum(timings["django_view_total_ms"]) / 1000.0)
    )

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "hardware": {
            "cpu": get_cpu_name(),
            "machine": platform.machine(),
            "logical_cpu_count": os.cpu_count(),
        },
        "environment": {
            "platform": platform.platform(),
            "python": sys.version.replace("\n", " "),
            "python_executable": sys.executable,
            "django_settings_module": os.environ.get("DJANGO_SETTINGS_MODULE"),
            "torch_version": torch.__version__,
            "torch_num_threads": torch.get_num_threads(),
            "torch_num_interop_threads": torch.get_num_interop_threads(),
            "cuda_available": torch.cuda.is_available(),
            "device": str(device),
            "ambient_model_path": str(settings.AMBIENT_MODEL_PATH),
        },
        "input_audio": {
            "format": "mono PCM16 WAV",
            "sample_rate_hz": args.sample_rate,
            "duration_seconds": args.duration,
            "bytes": len(audio_bytes),
            "decoded_sample_rate_hz": decoded_sample_rate,
            "decoded_duration_seconds": decoded_duration,
        },
        "warmup": {
            "runs_per_path": args.warmup,
            "excluded_from_metrics": True,
            "checkpoint_load_excluded": True,
        },
        "timing_scope": {
            "decode_ms": (
                "Upload read, WAV header validation, WAV decode to torch waveform, "
                "and duration validation. UploadedFile wrapper construction excluded."
            ),
            "preprocess_ms": (
                "Log-mel preprocessing from an already decoded waveform: mono mixdown, "
                "resampling when needed, duration fit, peak normalization, mel spectrogram, "
                "dB conversion, and feature standardization."
            ),
            "decode_preprocess_ms": "decode_ms and preprocess_ms together on a fresh upload.",
            "model_inference_ms": (
                "PyTorch model forward pass plus softmax/max on a precomputed feature tensor. "
                "Decode and preprocessing excluded."
            ),
            "ambient_service_total_ms": (
                "core.ambient.analyze_ambient_recording on a fresh UploadedFile: decode, "
                "preprocess, model inference, confidence extraction, and response context mapping. "
                "HTTP parsing, network transfer, and browser recording excluded."
            ),
            "django_view_total_ms": (
                "Direct DRF analyze_ambient view call using APIRequestFactory: multipart request "
                "parsing, permission/auth wrapper, ambient service processing, and JSON rendering. "
                "Network transfer, URL routing, middleware, runserver overhead, and browser recording excluded."
            ),
        },
        "prediction": prediction,
        "metrics": metrics,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    print(f"Saved benchmark report to {args.output}", flush=True)


if __name__ == "__main__":
    main()
