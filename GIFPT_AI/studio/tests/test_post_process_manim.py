"""Tests for post_process_manim_code.

Mocks openai and dotenv so no env vars or packages needed.
Run from GIFPT_AI/: python3 -m unittest studio.tests.test_post_process_manim
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Project root on path
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

# Mock external packages BEFORE importing llm_codegen
_mock_openai = MagicMock()
_mock_openai.OpenAI = MagicMock(return_value=MagicMock())
sys.modules.setdefault("openai", _mock_openai)
sys.modules.setdefault("dotenv", MagicMock())

from studio.ai.llm_codegen import post_process_manim_code  # noqa: E402


class TestPostProcessManim(unittest.TestCase):

    def test_strips_markdown_fences(self):
        code = "```python\nfrom manim import *\n```"
        result = post_process_manim_code(code)
        self.assertNotIn("```", result)

    def test_invalid_color_light_blue_replaced(self):
        code = "from manim import *\ncircle = Circle(color=LIGHT_BLUE)"
        result = post_process_manim_code(code)
        self.assertNotIn("LIGHT_BLUE", result)
        self.assertIn("BLUE_B", result)

    def test_invalid_color_cyan_replaced(self):
        code = "from manim import *\nsq = Square(color=CYAN)"
        result = post_process_manim_code(code)
        self.assertNotIn("CYAN", result)
        self.assertIn("TEAL", result)

    def test_invalid_color_brown_replaced(self):
        code = "color=BROWN"
        result = post_process_manim_code(code)
        self.assertNotIn("BROWN", result)
        self.assertIn("MAROON", result)

    def test_hex_color_replaced(self):
        code = 'rect = Rectangle(color="#abc123")'
        result = post_process_manim_code(code)
        self.assertNotIn("#abc123", result)
        self.assertIn("color=BLUE", result)

    def test_class_name_forced_to_algorithm_scene(self):
        code = "class BubbleSortScene(Scene):\n    pass"
        result = post_process_manim_code(code)
        self.assertIn("class AlgorithmScene(Scene)", result)
        self.assertNotIn("class BubbleSortScene", result)

    def test_unknown_helper_self_play_removed(self):
        code = (
            "from manim import *\n"
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        self.play(AddPointToGraph(x=1, y=2))\n"
            "        self.wait(1)\n"
        )
        result = post_process_manim_code(code)
        self.assertNotIn("AddPointToGraph", result)
        self.assertIn("self.wait(0.1)", result)

    def test_unknown_helper_bare_call_removed(self):
        code = (
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        PlotPoint(x=0, y=0)\n"
        )
        result = post_process_manim_code(code)
        self.assertNotIn("PlotPoint", result)

    def test_valid_code_unchanged_structure(self):
        code = (
            "from manim import *\n\n"
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        self.play(FadeIn(Circle(color=BLUE)))\n"
            "        self.wait(2)\n"
        )
        result = post_process_manim_code(code)
        self.assertIn("from manim import *", result)
        self.assertIn("class AlgorithmScene(Scene)", result)
        self.assertIn("FadeIn", result)

    def test_multiple_invalid_colors_all_replaced(self):
        code = "c1=Circle(color=LIGHT_BLUE); c2=Square(color=DARK_RED); c3=Text('x', color=VIOLET)"
        result = post_process_manim_code(code)
        for bad in ("LIGHT_BLUE", "DARK_RED", "VIOLET"):
            self.assertNotIn(bad, result)


if __name__ == "__main__":
    unittest.main()
