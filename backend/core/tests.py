from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token

from .models import Headphone, ListeningSession

User = get_user_model()


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

    def test_lists_brands(self):
        response = self.client.get("/api/headphones/brands/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"brands": ["Apple", "Sennheiser", "Sony"]})

    def test_filters_brands_by_connection_type(self):
        wired_response = self.client.get("/api/headphones/brands/?type=wired")
        bluetooth_response = self.client.get("/api/headphones/brands/?type=bluetooth")

        self.assertEqual(
            wired_response.json(),
            {"brands": ["Apple", "Sennheiser", "Sony"]},
        )
        self.assertEqual(
            bluetooth_response.json(),
            {"brands": ["Apple", "Sony"]},
        )

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
        self.assertEqual(response.json()["headphone"]["name"], "Apple AirPods Max")

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
                duration_minutes=0,
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
