from django.contrib.auth.models import Group
from rest_framework.test import APITestCase

from apps.accounts.models import User


class UserPinModelTest(APITestCase):
    """Tests for User.set_pin / check_pin model methods."""

    def setUp(self):
        self.user = User.objects.create_user(username="cajero", password="testpass123", role="CASHIER")

    def test_set_pin_stores_hash_and_check_pin_validates(self):
        self.user.set_pin("123456")
        self.user.save(update_fields=["pin_hash"])
        self.assertTrue(self.user.pin_hash)
        self.assertNotEqual(self.user.pin_hash, "123456")
        self.assertTrue(self.user.check_pin("123456"))

    def test_check_pin_rejects_wrong_pin(self):
        self.user.set_pin("123456")
        self.user.save(update_fields=["pin_hash"])
        self.assertFalse(self.user.check_pin("654321"))
        self.assertFalse(self.user.check_pin("000000"))

    def test_check_pin_fails_when_no_pin_set(self):
        self.assertEqual(self.user.pin_hash, "")
        self.assertFalse(self.user.check_pin("123456"))


class PinLoginViewTest(APITestCase):
    """Tests for POST /api/v1/auth/pin-login/."""

    URL = "/api/v1/auth/pin-login/"

    def setUp(self):
        self.user = User.objects.create_user(username="cajero", password="testpass123", role="CASHIER")
        self.user.set_pin("123456")
        self.user.save(update_fields=["pin_hash"])

    def test_returns_tokens_with_valid_pin(self):
        resp = self.client.post(self.URL, {"username": "cajero", "pin": "123456"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_returns_401_with_wrong_pin(self):
        resp = self.client.post(self.URL, {"username": "cajero", "pin": "000000"})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data["code"], "invalid_credentials")

    def test_returns_401_for_user_without_pin(self):
        user_no_pin = User.objects.create_user(username="sinpin", password="testpass123", role="CASHIER")
        resp = self.client.post(self.URL, {"username": "sinpin", "pin": "123456"})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data["code"], "invalid_credentials")

    def test_returns_401_for_inactive_user(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        resp = self.client.post(self.URL, {"username": "cajero", "pin": "123456"})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data["code"], "invalid_credentials")

    def test_returns_400_when_username_missing(self):
        resp = self.client.post(self.URL, {"pin": "123456"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "validation_error")

    def test_returns_400_when_pin_missing(self):
        resp = self.client.post(self.URL, {"username": "cajero"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "validation_error")

    def test_returns_400_when_both_missing(self):
        resp = self.client.post(self.URL, {})
        self.assertEqual(resp.status_code, 400)


class PinSetViewTest(APITestCase):
    """Tests for POST /api/v1/auth/pin/."""

    URL = "/api/v1/auth/pin/"

    def setUp(self):
        self.user = User.objects.create_user(username="cajero", password="testpass123", role="CASHIER")
        self._authenticate()

    def _authenticate(self):
        resp = self.client.post("/api/v1/auth/token/", {"username": "cajero", "password": "testpass123"})
        token = resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_set_pin_with_valid_password_and_6_digits(self):
        resp = self.client.post(self.URL, {"current_password": "testpass123", "pin": "654321"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["has_pin"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_pin("654321"))

    def test_remove_pin_with_null(self):
        self.user.set_pin("123456")
        self.user.save(update_fields=["pin_hash"])

        resp = self.client.post(self.URL, {"current_password": "testpass123", "pin": None}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["has_pin"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.pin_hash, "")

    def test_rejects_wrong_current_password(self):
        resp = self.client.post(self.URL, {"current_password": "wrongpass", "pin": "123456"})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data["code"], "invalid_credentials")

    def test_rejects_non_6_digit_pin_too_short(self):
        resp = self.client.post(self.URL, {"current_password": "testpass123", "pin": "1234"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "validation_error")

    def test_rejects_non_6_digit_pin_too_long(self):
        resp = self.client.post(self.URL, {"current_password": "testpass123", "pin": "12345678"})
        self.assertEqual(resp.status_code, 400)

    def test_rejects_non_numeric_pin(self):
        resp = self.client.post(self.URL, {"current_password": "testpass123", "pin": "abcdef"})
        self.assertEqual(resp.status_code, 400)

    def test_requires_authentication(self):
        self.client.credentials()  # Remove auth
        resp = self.client.post(self.URL, {"current_password": "testpass123", "pin": "123456"})
        self.assertEqual(resp.status_code, 401)


class UserListHasPinFieldTest(APITestCase):
    """Tests for has_pin field on GET /api/v1/users/."""

    URL = "/api/v1/users/"

    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="adminpass123", role="ADMIN")
        group, _ = Group.objects.get_or_create(name="ADMIN")
        self.admin.groups.set([group])
        self._authenticate()

    def _authenticate(self):
        resp = self.client.post("/api/v1/auth/token/", {"username": "admin", "password": "adminpass123"})
        token = resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_user_without_pin_has_pin_false(self):
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, 200)
        admin_data = next(u for u in resp.data["results"] if u["username"] == "admin")
        self.assertFalse(admin_data["has_pin"])

    def test_user_with_pin_has_pin_true(self):
        self.admin.set_pin("123456")
        self.admin.save(update_fields=["pin_hash"])

        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, 200)
        admin_data = next(u for u in resp.data["results"] if u["username"] == "admin")
        self.assertTrue(admin_data["has_pin"])
