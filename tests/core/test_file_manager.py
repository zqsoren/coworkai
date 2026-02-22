import unittest
import os
import shutil
import sys

# Ensure src is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.file_manager import FileManager

class TestFileManager(unittest.TestCase):
    TEST_DATA_ROOT = os.path.join(PROJECT_ROOT, "data_test")

    def setUp(self):
        # Clean up and recreate test data root
        if os.path.exists(self.TEST_DATA_ROOT):
            shutil.rmtree(self.TEST_DATA_ROOT)
        os.makedirs(self.TEST_DATA_ROOT)
        self.fm = FileManager(self.TEST_DATA_ROOT)
        
        # Create standard structure
        os.makedirs(os.path.join(self.TEST_DATA_ROOT, "workspace_test", "agent_a", "static"))
        os.makedirs(os.path.join(self.TEST_DATA_ROOT, "workspace_test", "agent_a", "active"))
        os.makedirs(os.path.join(self.TEST_DATA_ROOT, "workspace_test", "agent_a", "output"))

    def tearDown(self):
        if os.path.exists(self.TEST_DATA_ROOT):
            shutil.rmtree(self.TEST_DATA_ROOT)

    def test_root_lock(self):
        """Test strict root directory lock"""
        with self.assertRaises(PermissionError):
            self.fm.read_file("../outside.txt")
        
        with self.assertRaises(PermissionError):
            self.fm.write_file("/etc/passwd", "hack")
            
    def test_static_read_only(self):
        """Test static assets are read-only"""
        static_file = "workspace_test/agent_a/static/logo.txt"
        
        # Create file manually to test read
        full_path = os.path.join(self.TEST_DATA_ROOT, static_file)
        with open(full_path, "w") as f:
            f.write("logo content")
            
        # Read should succeed
        content = self.fm.read_file(static_file)
        self.assertEqual(content, "logo content")
        
        # Write should fail
        with self.assertRaises(PermissionError):
            self.fm.write_file(static_file, "new logo")

    def test_active_change_request(self):
        """Test active docs require approval for changes"""
        active_file = "workspace_test/agent_a/active/prd.md"
        
        # Initial write (force=True/new file logic allows direct write if not exists? 
        # Wait, if not exists, logic says: original="" -> returns Diff. 
        # But let's check write_file logic: "if tier == ACTIVE and not force: return ChangeRequest".
        # So even new files need approval unless forced.
        
        # Try writing new file without force
        cr = self.fm.write_file(active_file, "Initial content", force=False)
        self.assertIsNotNone(cr)
        self.assertEqual(cr.new_content, "Initial content")
        
        # Force write to simulate approval
        self.fm.write_file(active_file, "Initial content", force=True)
        self.assertEqual(self.fm.read_file(active_file), "Initial content")
        
        # Modify without force -> ChangeRequest
        cr = self.fm.write_file(active_file, "Updated content", force=False)
        self.assertIsNotNone(cr)
        self.assertIn("Updated content", cr.new_content)
        self.assertNotEqual(self.fm.read_file(active_file), "Updated content")

    def test_output_write_only(self):
        """Test output is write-only/append (no read allowed via FM)"""
        output_file = "workspace_test/agent_a/output/log.txt"
        
        # Write should succeed
        self.fm.write_file(output_file, "log entry")
        
        # Read should fail
        with self.assertRaises(PermissionError):
            self.fm.read_file(output_file)

if __name__ == "__main__":
    unittest.main()
