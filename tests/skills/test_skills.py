import unittest
import os
import sys
from unittest.mock import MagicMock, patch

# Ensure src is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.skills import deep_research, data_viz, browser_takeover
from src.skills.skill_loader import SkillLoader

class TestL2Skills(unittest.TestCase):
    def test_deep_research(self):
        """Test DeepResearch logic (mocked tools)"""
        # Mock LLM
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "Research Report Content"
        
        # Mock Tools
        mock_search = MagicMock()
        mock_search.invoke.return_value = "Title: Foo\n链接: http://foo.com"
        mock_fetch = MagicMock()
        mock_fetch.invoke.return_value = "Page Content"
        
        import asyncio
        # run is async
        result = asyncio.run(deep_research.run(
            "query", 
            llm=mock_llm, 
            search_tool=mock_search, 
            fetch_tool=mock_fetch
        ))
        
        self.assertIn("Research Report Content", result)

    def test_data_viz(self):
        """Test DataViz logic (mocked pandas/plt)"""
        # We can test data_viz by actually running it on a dummy CSV if pandas is installed
        # Or mock it. setup_env installed pandas.
        test_csv = "test_data.csv"
        with open(test_csv, "w") as f:
            f.write("col1,col2\nA,10\nB,20")
            
        try:
            res = data_viz.run(test_csv, chart_type="bar", output_dir="test_output")
            # If pandas not installed in test env (it should be in .venv), this might fail
            # But we assume .venv usage.
            # If it fails due to missing deps, we skip.
            if "依赖缺失" in res:
                print("Skipping DataViz test due to missing libs")
            else:
                self.assertIn("图表已保存", res)
                self.assertTrue(os.path.exists("test_output"))
        finally:
            if os.path.exists(test_csv):
                os.remove(test_csv)
            import shutil
            if os.path.exists("test_output"):
                shutil.rmtree("test_output")

    @patch("src.skills.browser_takeover._get_page")
    def test_browser_takeover(self, mock_get_page):
        """Test BrowserTakeover logic (mocked playwright)"""
        mock_page = MagicMock()
        mock_get_page.return_value = mock_page
        
        actions = [
            {"action": "goto", "url": "http://example.com"},
            {"action": "click", "selector": "#btn"}
        ]
        
        res = browser_takeover.run(actions)
        
        mock_page.goto.assert_called_with("http://example.com")
        mock_page.click.assert_called_with("#btn")
        self.assertIn("导航到", res)
        self.assertIn("点击", res)

    def test_skill_loader(self):
        """Test scanning standard skills"""
        loader = SkillLoader("dummy_custom_dir")
        count = loader.scan_and_load()
        self.assertGreaterEqual(count, 3) # deep_research, data_viz, browser_takeover
        self.assertIsNotNone(loader.get_skill("browser_takeover"))

if __name__ == "__main__":
    unittest.main()
