#!/usr/bin/env python3
"""
Post-deploy live API integration tests for the Cloud Run backend.

These tests call the deployed service directly and will create real DB records
and upload artifacts to GCS when running the order flow test.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


# Override via LIVE_API_BASE_URL env var when running against your own deployment.
DEFAULT_BASE_URL = os.getenv("LIVE_API_BASE_URL", "https://your-service-xxxxx-uc.a.run.app")
DEFAULT_IMAGE_NAME = "fotor-ai-20250301175637.jpg"


def _candidate_image_paths() -> list[Path]:
    env_path = os.getenv("LIVE_API_IMAGE_PATH")
    candidates = []
    if env_path:
        candidates.append(Path(env_path).expanduser())

    cwd = Path.cwd()
    candidates.extend(
        [
            cwd / DEFAULT_IMAGE_NAME,
            cwd / "tests" / "fixtures" / DEFAULT_IMAGE_NAME,
            Path.home() / "Downloads" / DEFAULT_IMAGE_NAME,
        ]
    )
    return candidates


def _find_image_path() -> Path | None:
    for path in _candidate_image_paths():
        if path.exists() and path.is_file():
            return path
    return None


class TestLiveCloudRunAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base_url = os.getenv("LIVE_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        if shutil.which("curl") is None:
            raise unittest.SkipTest("curl is required for live API tests")

    def _curl(self, args: list[str], timeout_seconds: int = 60, stdin_text: str | None = None) -> tuple[int, str]:
        cmd = [
            "curl",
            "-sS",
            "--max-time",
            str(timeout_seconds),
            "-o",
            "-",
            "-w",
            "\n__STATUS__:%{http_code}\n",
            *args,
        ]
        proc = subprocess.run(
            cmd,
            input=stdin_text,
            text=True,
            capture_output=True,
            timeout=timeout_seconds + 5,
        )

        if proc.returncode != 0:
            self.fail(f"curl failed (exit={proc.returncode}): {proc.stderr.strip()}")

        marker = "\n__STATUS__:"
        if marker not in proc.stdout:
            self.fail(f"Could not parse curl status. stdout={proc.stdout!r} stderr={proc.stderr!r}")

        body, status_part = proc.stdout.rsplit(marker, 1)
        status_str = status_part.strip()
        try:
            status_code = int(status_str)
        except ValueError:
            self.fail(f"Invalid status code from curl: {status_str!r}")
        return status_code, body

    def test_get_cost_returns_expected_fields(self) -> None:
        status_code, body = self._curl([f"{self.base_url}/getCost"], timeout_seconds=60)
        self.assertEqual(status_code, 200, msg=body)

        payload = json.loads(body)
        expected_keys = {
            "digital_cost_regular",
            "digital_cost_promotional",
            "pickup_cost_regular",
            "pickup_cost_promotional",
            "shipping_cost_regular",
            "shipping_cost_promotional",
        }
        self.assertTrue(expected_keys.issubset(payload.keys()), msg=json.dumps(payload, indent=2))

    def test_process_then_create_order_pickup(self) -> None:
        image_path = _find_image_path()
        if image_path is None:
            self.skipTest(
                "Test image not found. Set LIVE_API_IMAGE_PATH or place "
                f"{DEFAULT_IMAGE_NAME} in repo root or ~/Downloads."
            )

        status_code, body = self._curl(
            [
                "-X",
                "POST",
                "-F",
                f"file=@{image_path};type=image/jpeg",
                f"{self.base_url}/process",
            ],
            timeout_seconds=180,
        )
        self.assertEqual(status_code, 200, msg=body)
        process_payload = json.loads(body)
        self.assertIn("token", process_payload, msg=json.dumps(process_payload, indent=2))
        token = process_payload["token"]
        self.assertTrue(token)

        order_payload = {
            "email": "test@gmail.com",
            "fname": "Pickup",
            "lname": "User",
            "processed_image_token": token,
            "order_type": "pickup",
            "selected_layout": "4",
            "payment_info": {
                "gateway": "card",
                "amount": "6.99",
            },
            "pickupAddress": "2773 Ambrosia Way, Fairfield, CA, 94533",
        }

        status_code, body = self._curl(
            [
                "-X",
                "POST",
                "-H",
                "Content-Type: application/json",
                "--data-binary",
                "@-",
                f"{self.base_url}/createOrder",
            ],
            timeout_seconds=180,
            stdin_text=json.dumps(order_payload),
        )
        self.assertEqual(status_code, 200, msg=body)
        create_order_payload = json.loads(body)

        self.assertEqual(create_order_payload.get("order_token"), token, msg=json.dumps(create_order_payload, indent=2))
        self.assertIn("order_id", create_order_payload, msg=json.dumps(create_order_payload, indent=2))
        self.assertIn("external_order_token", create_order_payload, msg=json.dumps(create_order_payload, indent=2))
        self.assertIn("processed_image_url", create_order_payload, msg=json.dumps(create_order_payload, indent=2))
        self.assertIn("composite_image_url", create_order_payload, msg=json.dumps(create_order_payload, indent=2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
