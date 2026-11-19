"""Tests for authenticated mod.io subscription retrieval."""

import unittest
from unittest.mock import call, patch

from sandmod.modio import ModIOError, get_subscribed_mods


class SubscriptionTests(unittest.TestCase):
    @staticmethod
    def page(mods, offset, total):
        return {
            "data": mods,
            "result_count": len(mods),
            "result_offset": offset,
            "result_total": total,
        }

    def test_multiple_pages(self):
        first_page = [{"id": mod_id, "game_id": 254} for mod_id in range(1, 101)]
        second_page = [{"id": 101, "game_id": 254}]

        responses = [
            self.page(first_page, 0, 101),
            self.page(second_page, 100, 101),
        ]

        with patch(
            "sandmod.modio._get_authenticated",
            side_effect=responses,
        ) as request:
            mods = get_subscribed_mods(254, "test-pat")

        self.assertEqual(len(mods), 101)
        self.assertIn(1, mods)
        self.assertIn(101, mods)

        self.assertEqual(
            request.call_args_list,
            [
                call(
                    254,
                    "/me/subscribed",
                    "test-pat",
                    params={"game_id": 254, "_limit": 100, "_offset": 0},
                ),
                call(
                    254,
                    "/me/subscribed",
                    "test-pat",
                    params={"game_id": 254, "_limit": 100, "_offset": 100},
                ),
            ],
        )

    def test_empty_subscriptions(self):
        with patch(
            "sandmod.modio._get_authenticated",
            return_value=self.page([], 0, 0),
        ):
            mods = get_subscribed_mods(254, "test-pat")

        self.assertEqual(mods, {})

    def test_incomplete_pagination_fails(self):
        responses = [
            self.page([{"id": 1, "game_id": 254}], 0, 2),
            self.page([], 1, 2),
        ]

        with patch(
            "sandmod.modio._get_authenticated",
            side_effect=responses,
        ):
            with self.assertRaises(ModIOError):
                get_subscribed_mods(254, "test-pat")

    def test_later_http_failure_is_not_partial_success(self):
        responses = [
            self.page([{"id": 1, "game_id": 254}], 0, 2),
            ModIOError("mod.io rate limit reached", status_code=429),
        ]

        with patch(
            "sandmod.modio._get_authenticated",
            side_effect=responses,
        ):
            with self.assertRaises(ModIOError) as caught:
                get_subscribed_mods(254, "test-pat")

        self.assertEqual(caught.exception.status_code, 429)

    def test_duplicate_results_fail(self):
        responses = [
            self.page([{"id": 1, "game_id": 254}], 0, 2),
            self.page([{"id": 1, "game_id": 254}], 1, 2),
        ]

        with patch(
            "sandmod.modio._get_authenticated",
            side_effect=responses,
        ):
            with self.assertRaises(ModIOError):
                get_subscribed_mods(254, "test-pat")
