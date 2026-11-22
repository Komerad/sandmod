"""HTTP behavior without real mod.io requests."""

import unittest
from unittest.mock import Mock, patch

import requests

from sandmod.modio import ModIOError, _get, _get_authenticated


class ModIOHTTPTests(unittest.TestCase):
    def call_get(self):
        return _get(
            game_id=254,
            endpoint="/games/254/mods/42",
            api_key="secret-api-key",
            platform="windows",
        )

    def test_rate_limit_includes_retry_after(self):
        response = Mock(ok=False, status_code=429)
        response.headers = {"Retry-After": "120"}

        with patch("sandmod.modio.requests.get", return_value=response):
            with self.assertRaises(ModIOError) as caught:
                self.call_get()

        self.assertEqual(caught.exception.status_code, 429)
        self.assertIn("120", str(caught.exception))
        self.assertNotIn("secret-api-key", str(caught.exception))

    def test_rate_limit_without_retry_after(self):
        response = Mock(ok=False, status_code=429)
        response.headers = {}

        with patch("sandmod.modio.requests.get", return_value=response):
            with self.assertRaises(ModIOError) as caught:
                self.call_get()

        self.assertEqual(caught.exception.status_code, 429)
        self.assertIn("rate limit", str(caught.exception).lower())

    def test_server_error_does_not_leak_api_key(self):
        response = Mock(ok=False, status_code=503)
        response.headers = {}

        with patch("sandmod.modio.requests.get", return_value=response):
            with self.assertRaises(ModIOError) as caught:
                self.call_get()

        self.assertEqual(caught.exception.status_code, 503)
        self.assertIn("503", str(caught.exception))
        self.assertNotIn("secret-api-key", str(caught.exception))

    def test_network_failure_does_not_leak_url(self):
        error = requests.Timeout("Timed out fetching https://example.invalid/?api_key=secret-api-key")
        with patch("sandmod.modio.requests.get", side_effect=error):
            with self.assertRaises(ModIOError) as caught:
                self.call_get()

        self.assertNotIn("secret-api-key", str(caught.exception))

    def test_success_uses_platform_header(self):
        response = Mock(ok=True, status_code=200)
        response.json.return_value = {"id": 42, "name": "Test Mod"}

        with patch("sandmod.modio.requests.get", return_value=response) as request:
            result = self.call_get()

        self.assertEqual(result["id"], 42)
        self.assertEqual(request.call_args.kwargs["headers"]["X-Modio-Platform"], "windows")


class AuthenticatedModIOHTTPTests(unittest.TestCase):
    def test_request_uses_bearer_token(self):
        response = Mock(ok=True, status_code=200)
        response.json.return_value = {"data": [], "result_total": 0}

        with patch("sandmod.modio.requests.get", return_value=response) as request:
            result = _get_authenticated(
                254,
                "/me/subscribed",
                "test-pat",
                params={"game_id": 254, "_limit": 5},
            )

        self.assertEqual(result["result_total"], 0)

        args = request.call_args
        self.assertEqual(
            args.args[0],
            "https://g-254.modapi.io/v1/me/subscribed",
        )
        self.assertEqual(
            args.kwargs["headers"]["Authorization"],
            "Bearer test-pat",
        )
        self.assertNotIn("api_key", args.kwargs["params"])
        self.assertNotIn("X-Modio-Platform", args.kwargs["headers"])

    def test_unauthorized_does_not_expose_pat(self):
        response = Mock(ok=False, status_code=401)
        response.headers = {}

        with patch("sandmod.modio.requests.get", return_value=response):
            with self.assertRaises(ModIOError) as caught:
                _get_authenticated(254, "/me/subscribed", "test-pat")

        self.assertEqual(caught.exception.status_code, 401)
        self.assertNotIn("test-pat", str(caught.exception))

    def test_rate_limit_preserves_retry_after(self):
        response = Mock(ok=False, status_code=429)
        response.headers = {"Retry-After": "120"}

        with patch("sandmod.modio.requests.get", return_value=response):
            with self.assertRaises(ModIOError) as caught:
                _get_authenticated(254, "/me/subscribed", "test-pat")

        self.assertEqual(caught.exception.status_code, 429)
        self.assertIn("120", str(caught.exception))
        self.assertNotIn("test-pat", str(caught.exception))

    def test_network_failure_does_not_expose_pat(self):
        error = requests.Timeout("Request failed with Bearer test-pat")

        with patch("sandmod.modio.requests.get", side_effect=error):
            with self.assertRaises(ModIOError) as caught:
                _get_authenticated(254, "/me/subscribed", "test-pat")

        self.assertNotIn("test-pat", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
