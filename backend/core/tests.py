import io
import math
import tempfile
import wave
from datetime import timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
import torch

from .ambient import decode_uploaded_wav
from .exposure import exposure_percent_for_duration
from .ml.features import AudioPreprocessConfig, LogMelFeatureExtractor
from .ml.inference import EnvironmentAudioClassifier
from .ml.model import AmbientCNN
from .models import Headphone, ListeningSession

User = get_user_model()


def make_wav_upload(
    duration_seconds=4.0,
    sample_rate=16000,
    name="ambient-sample.wav",
):
    total_samples = int(duration_seconds * sample_rate)
    frames = bytearray()
    for index in range(total_samples):
        value = int(0.12 * 32767 * math.sin(2 * math.pi * 440 * index / sample_rate))
        frames.extend(value.to_bytes(2, byteorder="little", signed=True))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(bytes(frames))

    return SimpleUploadedFile(
        name,
        buffer.getvalue(),
        content_type="audio/wav",
    )


class HeadphoneApiTests(TestCase):
    def setUp(self):
        Headphone.objects.create(
            name="Apple AirPods Max",
            type="over-ear",
            connection="wireless",
            max_db_spl_wired="99-103 dB SPL @1mW (est.)",
            max_db_spl_bluetooth="103 dB SPL",
            notes="Premium ANC headphones.",
        )
        Headphone.objects.create(
            name="Sennheiser HD 600",
            type="over-ear",
            connection="wired",
            max_db_spl_wired="100 dB SPL @1mW",
            max_db_spl_bluetooth=None,
            notes="Open-back headphones.",
        )
        Headphone.objects.create(
            name="Sony WH-1000XM5",
            type="over-ear",
            connection="both",
            max_db_spl_wired="100 dB SPL @1mW",
            max_db_spl_bluetooth="105 dB SPL",
            notes="ANC headphones.",
        )
        Headphone.objects.create(
            name="Beats Solo Wireless",
            type="over-ear",
            connection="wireless",
            max_db_spl_wired=None,
            max_db_spl_bluetooth="104 dB SPL",
            notes="Bluetooth-only test headphones.",
        )
        Headphone.objects.create(
            name="Shure SRH440",
            type="over-ear",
            connection="wired",
            max_db_spl_wired="105 dB SPL @1mW",
            max_db_spl_bluetooth=None,
            notes="Wired-only test headphones.",
        )

    def test_lists_brands(self):
        response = self.client.get("/api/headphones/brands/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"brands": ["Apple", "Beats", "Sennheiser", "Shure", "Sony"]},
        )

    def test_filters_brands_by_connection_type(self):
        wired_response = self.client.get("/api/headphones/brands/?type=wired")
        bluetooth_response = self.client.get("/api/headphones/brands/?type=bluetooth")

        self.assertEqual(
            wired_response.json(),
            {"brands": ["Apple", "Sennheiser", "Shure", "Sony"]},
        )
        self.assertEqual(
            bluetooth_response.json(),
            {"brands": ["Apple", "Beats", "Sony"]},
        )

    def test_lists_only_models_with_selected_connection_spec(self):
        wired_beats = self.client.get("/api/headphones/?brand=Beats&type=wired")
        bluetooth_shure = self.client.get("/api/headphones/?brand=Shure&type=bluetooth")

        self.assertEqual(wired_beats.status_code, 200)
        self.assertEqual(wired_beats.json(), {"models": []})
        self.assertEqual(bluetooth_shure.status_code, 200)
        self.assertEqual(bluetooth_shure.json(), {"models": []})

    def test_lists_models_with_existing_response_shape(self):
        response = self.client.get("/api/headphones/?brand=Apple&type=bluetooth")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "models": [
                    {
                        "name": "Apple AirPods Max",
                        "type": "over-ear",
                        "connection": "wireless",
                        "max_dB_SPL_wired": "99-103 dB SPL @1mW (est.)",
                        "max_dB_SPL_bluetooth": "103 dB SPL",
                        "notes": "Premium ANC headphones.",
                    }
                ]
            },
        )

    def test_requires_brand_for_models(self):
        response = self.client.get("/api/headphones/")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "brand is required"})

    def test_runtime_api_does_not_read_json_file(self):
        with patch("builtins.open", side_effect=AssertionError("JSON file was read")):
            response = self.client.get("/api/headphones/?brand=Sony&type=bluetooth")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["models"][0]["name"], "Sony WH-1000XM5")


class AuthApiTests(TestCase):
    def test_register_creates_user_and_returns_token(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "ari",
                "email": "ari@example.com",
                "password": "StrongPass12345!",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("token", response.json())
        self.assertEqual(response.json()["user"]["username"], "ari")
        self.assertTrue(User.objects.filter(username="ari").exists())
        self.assertNotEqual(
            User.objects.get(username="ari").password,
            "StrongPass12345!",
        )

    def test_duplicate_registration_is_rejected(self):
        User.objects.create_user(username="ari", password="StrongPass12345!")

        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "ari",
                "password": "AnotherStrongPass12345!",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_valid_login_returns_token(self):
        User.objects.create_user(username="ari", password="StrongPass12345!")

        response = self.client.post(
            "/api/auth/login/",
            {
                "username": "ari",
                "password": "StrongPass12345!",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.json())
        self.assertEqual(response.json()["user"]["username"], "ari")

    def test_invalid_login_is_rejected(self):
        User.objects.create_user(username="ari", password="StrongPass12345!")

        response = self.client.post(
            "/api/auth/login/",
            {
                "username": "ari",
                "password": "wrong-password",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_authenticated_logout_deletes_token(self):
        user = User.objects.create_user(username="ari", password="StrongPass12345!")
        token = Token.objects.create(user=user)

        response = self.client.post(
            "/api/auth/logout/",
            HTTP_AUTHORIZATION=f"Token {token.key}",
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Token.objects.filter(user=user).exists())


class ListeningSessionApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ari",
            password="StrongPass12345!",
        )
        self.other_user = User.objects.create_user(
            username="maya",
            password="StrongPass12345!",
        )
        self.token = Token.objects.create(user=self.user)
        self.other_token = Token.objects.create(user=self.other_user)
        self.headphone = Headphone.objects.create(
            name="Apple AirPods Max",
            type="over-ear",
            connection="wireless",
            max_db_spl_wired="99-103 dB SPL @1mW (est.)",
            max_db_spl_bluetooth="103 dB SPL",
            notes="Premium ANC headphones.",
        )

    def auth_header(self, token=None):
        return {"HTTP_AUTHORIZATION": f"Token {(token or self.token).key}"}

    def session_payload(self, **overrides):
        payload = {
            "headphone_id": self.headphone.id,
            "connection_type": "bluetooth",
            "volume_percent": 50,
            "estimated_db": 52,
            "duration_minutes": 30,
        }
        payload.update(overrides)
        return payload

    def test_authenticated_user_can_create_session(self):
        response = self.client.post(
            "/api/sessions/",
            self.session_payload(),
            content_type="application/json",
            **self.auth_header(),
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(ListeningSession.objects.count(), 1)
        session = ListeningSession.objects.get()
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.headphone, self.headphone)
        self.assertFalse(session.ambient_analysis_used)
        self.assertIsNone(session.ambient_environment_class)
        self.assertIsNone(session.ambient_confidence)
        self.assertEqual(response.json()["headphone"]["name"], "Apple AirPods Max")
        self.assertFalse(response.json()["ambient_analysis_used"])

    def test_authenticated_user_can_create_session_with_ambient_metadata(self):
        response = self.client.post(
            "/api/sessions/",
            self.session_payload(
                ambient_analysis_used=True,
                ambient_environment_class="street_music",
                ambient_confidence=0.84,
            ),
            content_type="application/json",
            **self.auth_header(),
        )

        self.assertEqual(response.status_code, 201)
        session = ListeningSession.objects.get()
        self.assertEqual(session.user, self.user)
        self.assertTrue(session.ambient_analysis_used)
        self.assertEqual(session.ambient_environment_class, "street_music")
        self.assertEqual(session.ambient_confidence, 0.84)
        self.assertEqual(response.json()["ambient_environment_class"], "street_music")
        self.assertEqual(response.json()["ambient_confidence"], 0.84)

    def test_session_without_ambient_metadata_remains_valid(self):
        response = self.client.post(
            "/api/sessions/",
            self.session_payload(),
            content_type="application/json",
            **self.auth_header(),
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertFalse(body["ambient_analysis_used"])
        self.assertIsNone(body["ambient_environment_class"])
        self.assertIsNone(body["ambient_confidence"])

    def test_unauthenticated_session_creation_is_rejected(self):
        response = self.client.post(
            "/api/sessions/",
            self.session_payload(),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(ListeningSession.objects.count(), 0)

    def test_user_gets_only_their_sessions(self):
        own_session = ListeningSession.objects.create(
            user=self.user,
            headphone=self.headphone,
            connection_type="bluetooth",
            volume_percent=50,
            estimated_db=52,
            duration_minutes=30,
        )
        ListeningSession.objects.create(
            user=self.other_user,
            headphone=self.headphone,
            connection_type="bluetooth",
            volume_percent=80,
            estimated_db=82,
            duration_minutes=10,
        )

        response = self.client.get("/api/sessions/", **self.auth_header())

        self.assertEqual(response.status_code, 200)
        sessions = response.json()["sessions"]
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["id"], own_session.id)

    def test_one_user_cannot_retrieve_another_users_sessions(self):
        ListeningSession.objects.create(
            user=self.user,
            headphone=self.headphone,
            connection_type="bluetooth",
            volume_percent=50,
            estimated_db=52,
            duration_minutes=30,
        )

        response = self.client.get(
            "/api/sessions/",
            **self.auth_header(self.other_token),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"sessions": []})

    def test_session_validation_rejects_bad_values(self):
        response = self.client.post(
            "/api/sessions/",
            self.session_payload(
                connection_type="speaker",
                volume_percent=101,
                estimated_db=-1,
                duration_minutes=-1,
            ),
            content_type="application/json",
            **self.auth_header(),
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("connection_type", body)
        self.assertIn("volume_percent", body)
        self.assertIn("estimated_db", body)
        self.assertIn("duration_minutes", body)

    def test_session_validation_rejects_missing_headphone(self):
        response = self.client.post(
            "/api/sessions/",
            self.session_payload(headphone_id=9999),
            content_type="application/json",
            **self.auth_header(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("headphone", response.json())


class ListeningSessionLifecycleApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ari",
            password="StrongPass12345!",
        )
        self.other_user = User.objects.create_user(
            username="maya",
            password="StrongPass12345!",
        )
        self.token = Token.objects.create(user=self.user)
        self.other_token = Token.objects.create(user=self.other_user)
        self.headphone = Headphone.objects.create(
            name="Apple AirPods Pro",
            type="in-ear",
            connection="wireless",
            max_db_spl_wired=None,
            max_db_spl_bluetooth="103 dB SPL",
            notes="ANC earbuds.",
        )

    def auth_header(self, token=None):
        return {"HTTP_AUTHORIZATION": f"Token {(token or self.token).key}"}

    def start_payload(self, **overrides):
        payload = {
            "headphone_id": self.headphone.id,
            "connection_type": "bluetooth",
            "volume_percent": 70,
            "estimated_db": 85,
        }
        payload.update(overrides)
        return payload

    def start_session(self, now=None, **overrides):
        now = now or timezone.now()
        with patch("core.views.timezone.now", return_value=now):
            return self.client.post(
                "/api/sessions/start/",
                self.start_payload(**overrides),
                content_type="application/json",
                **self.auth_header(),
            )

    def test_starting_session_creates_active_owned_record(self):
        now = timezone.now()
        response = self.start_session(now=now)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(ListeningSession.objects.count(), 1)
        session = ListeningSession.objects.get()
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.status, ListeningSession.STATUS_ACTIVE)
        self.assertEqual(session.started_at, now)
        self.assertEqual(response.json()["session"]["status"], "active")

    def test_pause_resume_and_end_exclude_paused_time(self):
        t0 = timezone.now()
        response = self.start_session(now=t0)
        session_id = response.json()["session"]["id"]

        with patch("core.exposure.timezone.now", return_value=t0 + timedelta(minutes=10)):
            paused = self.client.post(
                f"/api/sessions/{session_id}/pause/",
                **self.auth_header(),
            )
        self.assertEqual(paused.status_code, 200)
        self.assertEqual(paused.json()["session"]["status"], "paused")
        self.assertEqual(paused.json()["session"]["actual_duration_seconds"], 600)

        with patch("core.exposure.timezone.now", return_value=t0 + timedelta(minutes=15)):
            resumed = self.client.post(
                f"/api/sessions/{session_id}/resume/",
                **self.auth_header(),
            )
        self.assertEqual(resumed.status_code, 200)
        self.assertEqual(resumed.json()["session"]["status"], "active")

        with patch("core.exposure.timezone.now", return_value=t0 + timedelta(minutes=25)):
            ended = self.client.post(
                f"/api/sessions/{session_id}/end/",
                **self.auth_header(),
            )
        self.assertEqual(ended.status_code, 200)
        body = ended.json()["session"]
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["actual_duration_seconds"], 1200)
        self.assertAlmostEqual(
            body["exposure_percent"],
            exposure_percent_for_duration(85, 1200),
            places=4,
        )

    def test_starting_again_recovers_existing_unfinished_session(self):
        first = self.start_session()
        second = self.start_session()

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["recovered"])
        self.assertEqual(ListeningSession.objects.count(), 1)
        self.assertEqual(
            first.json()["session"]["id"],
            second.json()["session"]["id"],
        )

    def test_user_cannot_mutate_another_users_session(self):
        response = self.start_session()
        session_id = response.json()["session"]["id"]

        blocked = self.client.post(
            f"/api/sessions/{session_id}/pause/",
            **self.auth_header(self.other_token),
        )

        self.assertEqual(blocked.status_code, 404)

    def test_daily_exposure_sums_multiple_sessions_and_can_exceed_100(self):
        now = timezone.now()
        for index, seconds in enumerate([28800, 14400]):
            exposure = exposure_percent_for_duration(85, seconds)
            ListeningSession.objects.create(
                user=self.user,
                headphone=self.headphone,
                connection_type="bluetooth",
                volume_percent=70,
                estimated_db=85,
                duration_minutes=math.ceil(seconds / 60),
                status=ListeningSession.STATUS_COMPLETED,
                started_at=now + timedelta(minutes=index),
                ended_at=now + timedelta(minutes=index, seconds=seconds),
                accumulated_duration_seconds=seconds,
                exposure_percent=exposure,
            )

        response = self.client.get("/api/sessions/today/", **self.auth_header())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["session_count"], 2)
        self.assertAlmostEqual(response.json()["total_exposure_percent"], 150.0)

    def test_daily_exposure_includes_active_session_so_far(self):
        now = timezone.now()
        ListeningSession.objects.create(
            user=self.user,
            headphone=self.headphone,
            connection_type="bluetooth",
            volume_percent=70,
            estimated_db=85,
            duration_minutes=0,
            status=ListeningSession.STATUS_ACTIVE,
            started_at=now - timedelta(hours=1),
            last_resumed_at=now - timedelta(hours=1),
        )

        with patch("core.exposure.timezone.now", return_value=now):
            response = self.client.get("/api/sessions/today/", **self.auth_header())

        self.assertEqual(response.status_code, 200)
        self.assertAlmostEqual(
            response.json()["total_exposure_percent"],
            round(exposure_percent_for_duration(85, 3600), 2),
        )

    def test_daily_summary_uses_local_day_boundary(self):
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        ListeningSession.objects.create(
            user=self.user,
            headphone=self.headphone,
            connection_type="bluetooth",
            volume_percent=70,
            estimated_db=85,
            status=ListeningSession.STATUS_COMPLETED,
            started_at=yesterday,
            ended_at=yesterday + timedelta(minutes=30),
            accumulated_duration_seconds=1800,
            exposure_percent=exposure_percent_for_duration(85, 1800),
        )
        ListeningSession.objects.create(
            user=self.user,
            headphone=self.headphone,
            connection_type="bluetooth",
            volume_percent=70,
            estimated_db=85,
            status=ListeningSession.STATUS_COMPLETED,
            started_at=now,
            ended_at=now + timedelta(minutes=30),
            accumulated_duration_seconds=1800,
            exposure_percent=exposure_percent_for_duration(85, 1800),
        )

        response = self.client.get("/api/sessions/today/", **self.auth_header())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["session_count"], 1)

    def test_edit_settings_finalizes_current_session_then_allows_new_session(self):
        t0 = timezone.now()
        response = self.start_session(now=t0)
        session_id = response.json()["session"]["id"]

        with patch("core.exposure.timezone.now", return_value=t0 + timedelta(minutes=35)):
            edited = self.client.post(
                f"/api/sessions/{session_id}/edit/",
                **self.auth_header(),
            )
        self.assertEqual(edited.status_code, 200)
        self.assertTrue(edited.json()["finalized_for_edit"])
        self.assertEqual(edited.json()["session"]["status"], "completed")
        self.assertEqual(edited.json()["session"]["actual_duration_seconds"], 2100)

        new_response = self.start_session(
            now=t0 + timedelta(minutes=36),
            volume_percent=55,
        )

        self.assertEqual(new_response.status_code, 201)
        self.assertNotEqual(new_response.json()["session"]["id"], session_id)
        self.assertEqual(ListeningSession.objects.count(), 2)
        self.assertGreater(new_response.json()["today"]["total_exposure_percent"], 0)

    def test_backward_compatible_session_without_lifecycle_timestamps(self):
        session = ListeningSession.objects.create(
            user=self.user,
            headphone=self.headphone,
            connection_type="bluetooth",
            volume_percent=70,
            estimated_db=85,
            duration_minutes=30,
        )

        response = self.client.get("/api/sessions/", **self.auth_header())

        self.assertEqual(response.status_code, 200)
        serialized = response.json()["sessions"][0]
        self.assertEqual(serialized["id"], session.id)
        self.assertEqual(serialized["actual_duration_seconds"], 1800)
        self.assertGreater(serialized["current_exposure_percent"], 0)


class AmbientUploadDecodingTests(SimpleTestCase):
    def test_decodes_valid_wav_without_persisting_audio(self):
        upload = make_wav_upload()

        waveform, sample_rate, duration_seconds = decode_uploaded_wav(upload)

        self.assertEqual(sample_rate, 16000)
        self.assertEqual(waveform.shape[0], 1)
        self.assertAlmostEqual(duration_seconds, 4.0, places=1)


class AmbientAnalysisApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ari",
            password="StrongPass12345!",
        )
        self.token = Token.objects.create(user=self.user)

    def auth_header(self):
        return {"HTTP_AUTHORIZATION": f"Token {self.token.key}"}

    def test_valid_audio_analysis_returns_environment_context(self):
        service_response = {
            "environment_class": "street_music",
            "environment_label": "Street Music",
            "confidence": 0.84,
            "analysis_used": True,
            "duration_seconds": 4.0,
            "context": {
                "label": "Street Music",
                "profile": "noisy public environment",
                "message": "A noisy public environment was detected.",
                "calibration_note": (
                    "This classifies the acoustic scene only; it does not measure ambient SPL."
                ),
            },
        }

        with patch(
            "core.views.ambient_service.analyze_ambient_recording",
            return_value=service_response,
        ) as analyze:
            response = self.client.post(
                "/api/ambient/analyze/",
                {"audio": make_wav_upload()},
                **self.auth_header(),
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["analysis_used"])
        self.assertEqual(body["environment_class"], "street_music")
        self.assertEqual(body["environment_label"], "Street Music")
        self.assertGreaterEqual(body["confidence"], 0.0)
        self.assertLessEqual(body["confidence"], 1.0)
        self.assertEqual(body["context"]["profile"], "noisy public environment")
        analyze.assert_called_once()

    def test_ambient_analysis_requires_authentication(self):
        response = self.client.post(
            "/api/ambient/analyze/",
            {"audio": make_wav_upload()},
        )

        self.assertEqual(response.status_code, 401)

    def test_missing_audio_is_rejected(self):
        response = self.client.post(
            "/api/ambient/analyze/",
            {},
            **self.auth_header(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("audio", response.json())

    def test_malformed_audio_is_rejected_cleanly(self):
        response = self.client.post(
            "/api/ambient/analyze/",
            {
                "audio": SimpleUploadedFile(
                    "ambient-sample.wav",
                    b"not a wav file",
                    content_type="audio/wav",
                )
            },
            **self.auth_header(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("audio", response.json())


class EnvironmentalAudioMlTests(SimpleTestCase):
    def test_preprocessing_output_shape(self):
        config = AudioPreprocessConfig(sample_rate=8000, duration_seconds=1.0, n_mels=32)
        extractor = LogMelFeatureExtractor(config)
        waveform = torch.randn(2, config.num_samples // 2)

        features = extractor.extract(waveform, sample_rate=8000)

        self.assertEqual(features.shape, (1, 32, config.expected_frames))

    def test_model_output_dimensions(self):
        model = AmbientCNN(num_classes=10)
        logits = model(torch.randn(4, 1, 64, 173))

        self.assertEqual(logits.shape, (4, 10))

    def test_checkpoint_loading_and_inference_response(self):
        config = AudioPreprocessConfig(sample_rate=8000, duration_seconds=1.0, n_mels=32)
        class_to_idx = {
            "air_conditioner": 0,
            "car_horn": 1,
            "children_playing": 2,
            "dog_bark": 3,
            "drilling": 4,
            "engine_idling": 5,
            "gun_shot": 6,
            "jackhammer": 7,
            "siren": 8,
            "street_music": 9,
        }
        model = AmbientCNN(num_classes=len(class_to_idx))

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = f"{tmpdir}/ambient_cnn.pt"
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "class_to_idx": class_to_idx,
                    "preprocess_config": config.to_dict(),
                },
                checkpoint_path,
            )

            classifier = EnvironmentAudioClassifier(checkpoint_path, device="cpu")
            prediction = classifier.predict_waveform(torch.randn(config.num_samples), config.sample_rate)

        self.assertIn(prediction["class"], class_to_idx)
        self.assertGreaterEqual(prediction["confidence"], 0.0)
        self.assertLessEqual(prediction["confidence"], 1.0)
        self.assertEqual(len(prediction["probabilities"]), 10)
