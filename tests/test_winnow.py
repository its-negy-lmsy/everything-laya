import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from everything_laya import LayaWinnow


class TestLayaWinnow(unittest.TestCase):
    def setUp(self):
        self.winnow = LayaWinnow()

    def test_winnow_preserves_errors_and_reduces_noise(self):
        lines = []
        for i in range(50):
            lines.append(f"[INFO] 2026-09-24 10:{i:02d}:00 downloading chunk_{i}.bin ... 100%")

        lines.extend([
            "Traceback (most recent call last):",
            '  File "src/auth/jwt.py", line 42, in decode_token',
            "    raise SignatureExpiredError('Token expired at timestamp 1727192800')",
            "SignatureExpiredError: Token expired at timestamp 1727192800",
            "FAILED: tests/test_auth.py::test_expired_token - Exit code: 1",
        ])

        for i in range(50):
            lines.append(f"[INFO] 2026-09-24 10:{i+10:02d}:00 clean cache worker idle")

        raw_log = "\n".join(lines)
        res = self.winnow.compact(raw_log, focus_query="SignatureExpiredError")

        self.assertGreater(res.original_lines, 100)
        self.assertLess(res.compacted_lines, res.original_lines)
        self.assertGreater(res.compression_ratio, 40.0)
        self.assertIn("Traceback (most recent call last):", res.text)
        self.assertIn("SignatureExpiredError", res.text)
        self.assertIn('line 42, in decode_token', res.text)


if __name__ == "__main__":
    unittest.main()
