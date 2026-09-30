from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from .ml.features import load_audio_bytes
from .ml.inference import EnvironmentAudioClassifier


AMBIENT_CLASS_CONTEXT = {
    "air_conditioner": {
        "label": "Air Conditioner",
        "profile": "steady background noise",
        "message": (
            "A steady background sound was detected. It does not change the "
            "headphone exposure estimate, but steady noise can make people turn "
            "music up without noticing."
        ),
    },
    "car_horn": {
        "label": "Car Horn",
        "profile": "sudden street noise",
        "message": (
            "A sudden street-noise context was detected. Keep the headphone "
            "estimate separate from the environment, and avoid raising volume to "
            "compete with short loud events."
        ),
    },
    "children_playing": {
        "label": "Children Playing",
        "profile": "active background noise",
        "message": (
            "An active background environment was detected. If the room feels busy, "
            "better isolation can help you avoid creeping the volume upward."
        ),
    },
    "dog_bark": {
        "label": "Dog Bark",
        "profile": "intermittent background noise",
        "message": (
            "An intermittent background sound was detected. Short sounds do not "
            "change the NIOSH headphone estimate, but they can still tempt volume "
            "increases."
        ),
    },
    "drilling": {
        "label": "Drilling",
        "profile": "noisy environment",
        "message": (
            "A noisy work-like environment was detected. Consider reducing playback "
            "volume or using better isolation instead of competing with the room."
        ),
    },
    "engine_idling": {
        "label": "Engine Idling",
        "profile": "steady transportation noise",
        "message": (
            "A steady transportation-like sound was detected. Low background rumble "
            "often leads listeners to raise volume, especially with open or leaky "
            "headphones."
        ),
    },
    "gun_shot": {
        "label": "Gun Shot",
        "profile": "impulsive loud sound",
        "message": (
            "An impulsive loud-sound class was detected. This classifier does not "
            "measure the room level, so treat the result as context and avoid "
            "masking the environment with higher playback."
        ),
    },
    "jackhammer": {
        "label": "Jackhammer",
        "profile": "very noisy environment",
        "message": (
            "A very noisy environment class was detected. Your headphone exposure "
            "estimate stays the same, but this is a strong cue to lower volume or "
            "use isolation/noise cancellation."
        ),
    },
    "siren": {
        "label": "Siren",
        "profile": "loud alerting sound",
        "message": (
            "An alerting street-sound class was detected. Keep awareness of your "
            "surroundings and avoid turning headphones up to cover the environment."
        ),
    },
    "street_music": {
        "label": "Street Music",
        "profile": "noisy public environment",
        "message": (
            "A noisy public environment was detected. People often raise listening "
            "volume around music or crowd noise, so consider isolation or a lower "
            "setting."
        ),
    },
}


class AmbientModelUnavailable(RuntimeError):
    pass


def environment_label(environment_class: str) -> str:
    context = AMBIENT_CLASS_CONTEXT.get(environment_class)
    if context:
        return context["label"]
    return environment_class.replace("_", " ").title()


def environment_context(environment_class: str) -> dict:
    context = AMBIENT_CLASS_CONTEXT.get(environment_class, {})
    return {
        "label": environment_label(environment_class),
        "profile": context.get("profile", "environmental sound"),
        "message": context.get(
            "message",
            "An environmental sound was detected. Use this as context, not as a "
            "calibrated room noise measurement.",
        ),
        "calibration_note": (
            "This classifies the acoustic scene only; it does not measure ambient SPL."
        ),
    }


@lru_cache(maxsize=1)
def get_ambient_classifier() -> EnvironmentAudioClassifier:
    checkpoint_path = Path(settings.AMBIENT_MODEL_PATH)
    if not checkpoint_path.exists():
        raise AmbientModelUnavailable(
            f"Ambient model checkpoint was not found at {checkpoint_path}."
        )
    return EnvironmentAudioClassifier(
        checkpoint_path=checkpoint_path,
        device=settings.AMBIENT_MODEL_DEVICE,
    )


def clear_ambient_classifier_cache() -> None:
    get_ambient_classifier.cache_clear()


def _validate_wav_bytes(data: bytes) -> None:
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise serializers.ValidationError(
            {"audio": "Upload must be a WAV audio file."}
        )


def decode_uploaded_wav(uploaded_file) -> tuple:
    max_bytes = settings.AMBIENT_AUDIO_MAX_UPLOAD_BYTES
    data = uploaded_file.read(max_bytes + 1)
    if not data:
        raise serializers.ValidationError({"audio": "Audio file is empty."})
    if len(data) > max_bytes:
        raise serializers.ValidationError(
            {"audio": f"Audio file must be {max_bytes} bytes or smaller."}
        )

    _validate_wav_bytes(data)

    try:
        waveform, sample_rate = load_audio_bytes(data, suffix=".wav")
    except Exception as exc:
        raise serializers.ValidationError(
            {"audio": "Audio file could not be decoded."}
        ) from exc

    duration_seconds = waveform.shape[-1] / float(sample_rate)
    min_seconds = settings.AMBIENT_AUDIO_MIN_SECONDS
    max_seconds = settings.AMBIENT_AUDIO_MAX_SECONDS
    if duration_seconds < min_seconds or duration_seconds > max_seconds:
        raise serializers.ValidationError(
            {
                "audio": (
                    "Audio duration must be between "
                    f"{min_seconds:g} and {max_seconds:g} seconds."
                )
            }
        )

    return waveform, sample_rate, duration_seconds


def analyze_ambient_recording(uploaded_file) -> dict:
    waveform, sample_rate, duration_seconds = decode_uploaded_wav(uploaded_file)
    classifier = get_ambient_classifier()
    prediction = classifier.predict_waveform(waveform, sample_rate)
    environment_class = prediction["class"]
    confidence = float(prediction["confidence"])

    return {
        "environment_class": environment_class,
        "environment_label": environment_label(environment_class),
        "confidence": confidence,
        "analysis_used": True,
        "duration_seconds": round(duration_seconds, 2),
        "context": environment_context(environment_class),
    }
