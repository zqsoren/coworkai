import unittest
import os
import sys

# Ensure src is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.ui.diff_viewer import render_diff_lines

class TestUIComponents(unittest.TestCase):
    def test_render_diff_lines(self):
        diff = [
            "--- old.txt",
            "+++ new.txt",
            "@@ -1,1 +1,1 @@",
            "-old line",
            "+new line",
            " common line"
        ]
        html = render_diff_lines(diff)
        
        self.assertIn('<div style="color: #f87171', html) # Red for deletion
        self.assertIn('<div style="color: #4ade80', html) # Green for addition
        self.assertIn("old line", html)
        self.assertIn("new line", html)

if __name__ == "__main__":
    unittest.main()
