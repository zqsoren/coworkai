import unittest
import os
import sys
from unittest.mock import MagicMock, patch

# Ensure src is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.tools.file_tools import init_file_tools, read_file, write_file
from src.tools.code_tools import python_repl, shell_command
from src.tools.browser_tools import get_current_time

class TestL1Tools(unittest.TestCase):
    def test_file_tools(self):
        """Test FileSystemTools wrapper"""
        mock_fm = MagicMock()
        mock_fm.read_file.return_value = "content"
        mock_fm.write_file.return_value = None # success
        
        init_file_tools(mock_fm)
        
        # Test read
        self.assertEqual(read_file.invoke("test.txt"), "content")
        mock_fm.read_file.assert_called_with("test.txt")
        
        # Test write
        res = write_file.invoke({"path": "test.txt", "content": "new"})
        self.assertIn("文件已写入", res)
        mock_fm.write_file.assert_called_with("test.txt", "new")

    def test_code_tools(self):
        """Test CodeTools"""
        # Python REPL
        res = python_repl.invoke("print(1+1)")
        self.assertIn("2", res)
        
        res = python_repl.invoke("x=10")
        self.assertIn("无输出", res)
        
        # Shell (Allowed)
        res = shell_command.invoke("echo hello")
        self.assertIn("hello", res)
        
        # Shell (Forbidden)
        res = shell_command.invoke("rm -rf /")
        self.assertIn("安全拒绝", res)

    def test_browser_primitives(self):
        """Test BrowserPrimitives"""
        time_str = get_current_time.invoke({})
        self.assertIn(":", time_str)
        self.assertIn("-", time_str)

if __name__ == "__main__":
    unittest.main()
