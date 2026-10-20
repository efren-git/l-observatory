"""Synthetic tests for the pairs position logic."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from inercia.pairs import _positions  # noqa: E402


class PairsTest(unittest.TestCase):
    def test_entry_exit_directions(self):
        z = pd.Series([3.0, 2.5, 0.0, -3.0, -2.5, 0.0])
        pos = _positions(z, entry=2.0, exit=0.5, max_hold=60)
        self.assertEqual(pos.tolist(), [-1.0, -1.0, 0.0, 1.0, 1.0, 0.0])

    def test_max_hold_forces_exit(self):
        z = pd.Series([3.0, 3.0, 3.0, 3.0, 3.0])
        pos = _positions(z, entry=2.0, exit=0.5, max_hold=2)
        self.assertEqual(pos.tolist(), [-1.0, -1.0, 0.0, -1.0, -1.0])


if __name__ == "__main__":
    unittest.main()
