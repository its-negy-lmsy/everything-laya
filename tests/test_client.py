import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from everything_laya import LayaClient


class TestLayaClient(unittest.TestCase):
    def setUp(self):
        self.client = LayaClient("http://127.0.0.1:8080")

    def test_client_initialization(self):
        self.assertEqual(self.client.base_url, "http://127.0.0.1:8080")
        self.assertEqual(self.client.predict_url, "http://127.0.0.1:8080/predict")

    def test_client_live_server_prediction(self):
        if not self.client.is_alive():
            self.skipTest("Laya daemon is not running on 127.0.0.1:8080")

        is_safe, conf = self.client.noul("ls -la", "Is this a harmless read-only command?")
        self.assertIsInstance(is_safe, bool)
        self.assertTrue(0.0 <= conf <= 1.0)

    def test_client_choose(self):
        if not self.client.is_alive():
            self.skipTest("Laya daemon is not running on 127.0.0.1:8080")

        choice, conf = self.client.choose(
            state="Fix the NullPointerException in user_service.py",
            instructions="What category is this ticket?",
            criteria={"bug": "code bug or crash", "feature": "new feature request", "docs": "documentation update"}
        )
        self.assertIn(choice, ("bug", "feature", "docs"))
        self.assertEqual(choice, "bug")
        self.assertGreater(conf, 0.4)


if __name__ == "__main__":
    unittest.main()
