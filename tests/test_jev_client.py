from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from scripts.jev_client import JevError, decide


class JevClientTests(unittest.TestCase):
    def test_typesafe_request_shape(self) -> None:
        response = {
            "model": "jev-1.13.0",
            "answers": {"intent": {"type": "noul", "noul": 0.9}},
            "usage": {"input_tokens": 10},
            "provider": "TypeSafe",
            "id": "req-1",
        }
        with patch("scripts.jev_client._post", return_value=response) as post:
            result = decide(
                {"message": "refund"},
                {"intent": {"type": "noul", "instructions": "Refund?"}},
                provider="typesafe",
                api_key="secret",
            )

        url, payload, headers, _timeout = post.call_args.args
        self.assertEqual(url, "https://api.typesafe.ai/v1/systemone")
        self.assertEqual(payload["model"], "jev-latest")
        self.assertEqual(payload["state"], {"message": "refund"})
        self.assertEqual(headers["Authorization"], "Bearer secret")
        self.assertEqual(result.request_id, "req-1")

    def test_openrouter_request_shape(self) -> None:
        response = {
            "model": "typesafe/jev-1.13-20260917",
            "answers": {"intent": {"type": "noul", "noul": 0.8}},
            "usage": {},
            "provider": "TypeSafe",
        }
        with patch("scripts.jev_client._post", return_value=response) as post:
            decide(
                "message",
                {"intent": {"type": "noul", "instructions": "Refund?"}},
                provider="openrouter",
                api_key="secret",
            )

        url, payload, headers, _timeout = post.call_args.args
        self.assertEqual(url, "https://openrouter.ai/api/alpha/decisions")
        self.assertEqual(payload["model"], "~typesafe/jev-latest")
        self.assertIn("HTTP-Referer", headers)
        self.assertIn("X-Title", headers)

    def test_missing_key_fails_before_request(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch(
            "scripts.jev_client._post"
        ) as post:
            with self.assertRaises(JevError):
                decide("state", {"q": {"type": "noul", "instructions": "ok?"}}, provider="typesafe")
        post.assert_not_called()

    def test_transient_error_retries(self) -> None:
        response = {
            "answers": {"q": {"type": "noul", "noul": 0.5}},
            "model": "jev-latest",
            "usage": {},
        }
        with patch(
            "scripts.jev_client._post",
            side_effect=[JevError("HTTP 429: retry"), response],
        ) as post, patch("scripts.jev_client.time.sleep") as sleep:
            decide(
                "state",
                {"q": {"type": "noul", "instructions": "ok?"}},
                provider="typesafe",
                api_key="secret",
                retries=1,
                retry_base_seconds=0,
            )

        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once()

    def test_auth_error_does_not_retry(self) -> None:
        with patch(
            "scripts.jev_client._post",
            side_effect=JevError("HTTP 401: unauthorized"),
        ) as post:
            with self.assertRaises(JevError):
                decide(
                    "state",
                    {"q": {"type": "noul", "instructions": "ok?"}},
                    provider="typesafe",
                    api_key="secret",
                    retries=3,
                )
        self.assertEqual(post.call_count, 1)

    def test_missing_answers_fails(self) -> None:
        with patch("scripts.jev_client._post", return_value={"model": "jev-latest"}):
            with self.assertRaises(JevError):
                decide(
                    "state",
                    {"q": {"type": "noul", "instructions": "ok?"}},
                    provider="typesafe",
                    api_key="secret",
                )


if __name__ == "__main__":
    unittest.main()

