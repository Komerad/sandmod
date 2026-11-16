"""HTTP behavior without real mod.io requests."""

import unittest
from unittest.mock import Mock, patch

import requests

from sandmod.modio import ModIOError, _get


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


if __name__ == "__main__":
    unittest.main()
