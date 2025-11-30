# app/llm_codegen.py
import os, json, re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Valid Manim colors (from manim.utils.color)
VALID_MANIM_COLORS = [
    "WHITE", "BLACK", "GRAY", "GREY",
    "BLUE", "BLUE_A", "BLUE_B", "BLUE_C", "BLUE_D", "BLUE_E",
    "RED", "RED_A", "RED_B", "RED_C", "RED_D", "RED_E",
    "GREEN", "GREEN_A", "GREEN_B", "GREEN_C", "GREEN_D", "GREEN_E",
    "YELLOW", "YELLOW_A", "YELLOW_B", "YELLOW_C", "YELLOW_D", "YELLOW_E",
    "PURPLE", "PURPLE_A", "PURPLE_B", "PURPLE_C", "PURPLE_D", "PURPLE_E",
    "ORANGE", "PINK", "TEAL", "TEAL_A", "TEAL_B", "TEAL_C", "TEAL_D", "TEAL_E",
    "GOLD", "GOLD_A", "GOLD_B", "GOLD_C", "GOLD_D", "GOLD_E",
    "MAROON", "MAROON_A", "MAROON_B", "MAROON_C", "MAROON_D", "MAROON_E",
    "LIGHT_GRAY", "LIGHT_GREY", "DARK_GRAY", "DARK_GREY",
    "LIGHT_BROWN", "DARK_BROWN", "GRAY_BROWN",
    "LIGHT_PINK", "PURE_RED", "PURE_GREEN", "PURE_BLUE"
]

REFERENCE_PATH = "app/render_cnn_matrix.py"
with open(REFERENCE_PATH, "r", encoding="utf-8") as f:
    reference_code = f.read()

SYSTEM_PROMPT = f"""
You are a Manim code generator.
You will receive a structured animation IR (entities, layout, actions)
and must produce a complete, executable Python script using Manim.

Below is a **reference example** of excellent Manim code style
(from render_cnn_matrix). Follow this level of structure, clarity, and animation pacing.

<reference_example>
{reference_code}
</reference_example>

CRITICAL COLOR RULES:
You MUST ONLY use these exact Manim color constants:
- Basic: WHITE, BLACK, GRAY, GREY
- Blue: BLUE, BLUE_A, BLUE_B, BLUE_C, BLUE_D, BLUE_E
- Red: RED, RED_A, RED_B, RED_C, RED_D, RED_E
- Green: GREEN, GREEN_A, GREEN_B, GREEN_C, GREEN_D, GREEN_E
- Yellow: YELLOW, YELLOW_A, YELLOW_B, YELLOW_C, YELLOW_D, YELLOW_E
- Purple: PURPLE, PURPLE_A, PURPLE_B, PURPLE_C, PURPLE_D, PURPLE_E
- Orange: ORANGE
- Pink: PINK, LIGHT_PINK
- Teal: TEAL, TEAL_A, TEAL_B, TEAL_C, TEAL_D, TEAL_E
- Gold: GOLD, GOLD_A, GOLD_B, GOLD_C, GOLD_D, GOLD_E
- Others: MAROON, LIGHT_GRAY, DARK_GRAY

❌ FORBIDDEN COLORS (DO NOT USE):
LIGHT_BLUE, DARK_BLUE, LIGHT_RED, DARK_RED, LIGHT_GREEN, DARK_GREEN,
CYAN, MAGENTA, VIOLET, INDIGO, BROWN

If you need variations, use the _A, _B, _C, _D, _E suffixes (e.g., BLUE_B for lighter blue).

IMPORTANT RULES:
- Always include: `from manim import *`
- Use ONLY the color constants listed above
- NEVER use hex color strings like "#abcdef"
- NEVER compare color objects or convert them to strings
- DO NOT invent custom helper functions or animations not in Manim. Use only built-in mobjects and animations (FadeIn/FadeOut/Create/Transform/Indicate/MoveToTarget, mobject.animate, etc.). If you want to "plot/add a point", create a Dot at a valid position (optionally using Axes.coords_to_point) and play FadeIn/Move animations.


Style rules you MUST follow:
1. Must start with 'from manim import *'.
2. Define a class named AlgorithmScene(Scene) with construct(self).
3. Use same object naming conventions as the reference (Square, Text, SurroundingRectangle, etc.).
4. Use consistent color palette from the valid colors above.
5. Animate logically: FadeIn → Move → Transform → Highlight → FadeOut.
6. Add descriptive labels (Text) near key components, similar to the CNN example.
7. Avoid duplicate keyword arguments or redeclarations (like color twice).
8. Output ONLY valid Python code (no markdown, no prose).
9. End with self.wait(2).
"""

def build_prompt_codegen(anim_ir: dict) -> str:
    return f"""
You are a Manim expert. Convert the following structured animation IR into a **complete** Manim Scene.

IR:
{json.dumps(anim_ir, indent=2, ensure_ascii=False)}

CRITICAL Requirements:
0. Shapes: The examples below cover common shapes (matrix, array, rectangle, circle) but you are NOT limited to these. If the IR contains an unrecognized shape, choose the closest Manim primitive (Rectangle, Circle, Line, Arrow, Dot, Polygon) and render it with available label/data/dimensions.
0b. DO NOT call or reference undefined helper functions (e.g., AddPointToGraph, PlotPoint, CreateGraph). Only use Manim core classes and animations. For points on axes, create a Dot and position it via Axes.coords_to_point(x, y).
1. **Render shapes according to their type:**
   
   A) For "matrix" shape with "data" field:
   ```python
   values = [[1,2,3], [4,5,6], [7,8,9]]  # from IR data field
   cells = []
   for r in range(len(values)):
       for c in range(len(values[0])):
           sq = Square(side_length=0.5, color=BLUE_B, fill_opacity=0.3)
           txt = Text(str(values[r][c]), font_size=20, color=WHITE)
           cells.append(VGroup(sq, txt))
   matrix = VGroup(*cells).arrange_in_grid(rows=len(values), cols=len(values[0]), buff=0.05)
   label = Text("Input", font_size=24, color=WHITE).next_to(matrix, UP)
   matrix_group = VGroup(matrix, label).move_to([x, y, 0])
   ```
   
   B) For "array" shape with "data" field:
   ```python
   values = [10, 20, 30, 40]  # from IR data field
   items = []
   for val in values:
       sq = Square(side_length=0.6, color=RED_B, fill_opacity=0.3)
       txt = Text(str(val), font_size=20, color=WHITE)
       items.append(VGroup(sq, txt))
   array = VGroup(*items).arrange(RIGHT, buff=0.1)
   label = Text("Array", font_size=24, color=WHITE).next_to(array, UP)
   array_group = VGroup(array, label).move_to([x, y, 0])
   ```
   
   C) For "rectangle" or "circle" with "label" field only:
   ```python
   rect = Rectangle(width=2.0, height=1.0, color=YELLOW, fill_opacity=0.3)
   label = Text("Q", font_size=24, color=WHITE)
   obj = VGroup(rect, label).move_to([x, y, 0])
   ```
   
   D) For shapes without "label" (decorative):
   ```python
   circle = Circle(radius=0.5, color=ORANGE).move_to([x, y, 0])
   ```

2. **Use "dimensions" field if present** (e.g., "3×3", "(seq_len, d_model)"):
   - Add as small text annotation below or next to the object

3. **Must visualize every operation sequentially** — no skipping.

4. Add subtle pauses (`self.wait(0.3)`) between major steps.

5. End with fade-out of all objects.

Output:
- Write **only Python code** that defines `class AlgorithmScene(Scene)`.
- Do not include markdown (no ```python or ```).
- Code must be directly executable by `manim`.
"""



def call_llm_codegen(anim_ir: dict):
    prompt = build_prompt_codegen(anim_ir)
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    code = resp.choices[0].message.content

    code = code.replace("```python", "").replace("```", "").strip()
    
    # Fix invalid colors - map to valid alternatives
    INVALID_COLOR_MAP = {
        'LIGHT_BLUE': 'BLUE_B',
        'DARK_BLUE': 'BLUE_D',
        'LIGHT_RED': 'RED_B',
        'DARK_RED': 'RED_D',
        'LIGHT_GREEN': 'GREEN_B',
        'DARK_GREEN': 'GREEN_D',
        'LIGHT_YELLOW': 'YELLOW_B',
        'DARK_YELLOW': 'YELLOW_D',
        'CYAN': 'TEAL',
        'MAGENTA': 'PINK',
        'VIOLET': 'PURPLE',
        'INDIGO': 'PURPLE_D',
        'BROWN': 'MAROON',
        'LIME': 'GREEN_B',
        'NAVY': 'BLUE_D',
    }
    
    for invalid, valid in INVALID_COLOR_MAP.items():
        # Replace in color= arguments
        code = re.sub(rf'\bcolor\s*=\s*{invalid}\b', f'color={valid}', code)
        # Replace standalone color references
        code = re.sub(rf'\b{invalid}\b(?=\s*[,\)])', valid, code)
    
    # Remove hex colors - replace with named colors
    code = re.sub(r'color\s*=\s*["\']#[0-9A-Fa-f]{6}["\']', 'color=BLUE', code)
    
    # Force class name to AlgorithmScene
    code = re.sub(r'class\s+\w+Scene\s*\(Scene\)', 'class AlgorithmScene(Scene)', code)

    # Strip invented helper calls that cause NameError; replace with small wait to preserve pacing
    UNKNOWN_HELPERS = [
        'AddPointToGraph', 'PlotPoint', 'CreateGraph', 'AnimateCurvePoint',
        'DrawArrowBetween', 'ShowValueOnPlot'
    ]
    for name in UNKNOWN_HELPERS:
        # Remove lines like: self.play(AddPointToGraph(...)) → self.wait(0.1)
        code = re.sub(rf'^\s*self\.play\(\s*{name}\([^)]*\)\s*\)\s*$', '        self.wait(0.1)', code, flags=re.M)
        # Also remove any bare calls `${name}(...)`
        code = re.sub(rf'^\s*{name}\([^)]*\)\s*$', '        self.wait(0.1)', code, flags=re.M)
    
    return code

def call_llm_codegen_with_usage(anim_ir: dict):
    prompt = build_prompt_codegen(anim_ir)
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    code = resp.choices[0].message.content
    code = code.replace("```python", "").replace("```", "").strip()

    # post-processing mirrors call_llm_codegen
    INVALID_COLOR_MAP = {
        'LIGHT_BLUE': 'BLUE_B',
        'DARK_BLUE': 'BLUE_D',
        'LIGHT_RED': 'RED_B',
        'DARK_RED': 'RED_D',
        'LIGHT_GREEN': 'GREEN_B',
        'DARK_GREEN': 'GREEN_D',
        'LIGHT_YELLOW': 'YELLOW_B',
        'DARK_YELLOW': 'YELLOW_D',
        'CYAN': 'TEAL',
        'MAGENTA': 'PINK',
        'VIOLET': 'PURPLE',
        'INDIGO': 'PURPLE_D',
        'BROWN': 'MAROON',
        'LIME': 'GREEN_B',
        'NAVY': 'BLUE_D',
    }
    for invalid, valid in INVALID_COLOR_MAP.items():
        code = re.sub(rf'\bcolor\s*=\s*{invalid}\b', f'color={valid}', code)
        code = re.sub(rf'\b{invalid}\b(?=\s*[,\)])', valid, code)
    code = re.sub(r'color\s*=\s*["\']#[0-9A-Fa-f]{6}["\']', 'color=BLUE', code)
    code = re.sub(r'class\s+\w+Scene\s*\(Scene\)', 'class AlgorithmScene(Scene)', code)

    UNKNOWN_HELPERS = [
        'AddPointToGraph', 'PlotPoint', 'CreateGraph', 'AnimateCurvePoint',
        'DrawArrowBetween', 'ShowValueOnPlot'
    ]
    for name in UNKNOWN_HELPERS:
        code = re.sub(rf'^\s*self\.play\(\s*{name}\([^)]*\)\s*\)\s*$', '        self.wait(0.1)', code, flags=re.M)
        code = re.sub(rf'^\s*{name}\([^)]*\)\s*$', '        self.wait(0.1)', code, flags=re.M)

    usage = getattr(resp, "usage", None)
    if usage:
        usage_dict = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None) or (usage.get("prompt_tokens") if hasattr(usage, "get") else None),
            "completion_tokens": getattr(usage, "completion_tokens", None) or (usage.get("completion_tokens") if hasattr(usage, "get") else None),
            "total_tokens": getattr(usage, "total_tokens", None) or (usage.get("total_tokens") if hasattr(usage, "get") else None),
        }
    else:
        usage_dict = None

    return code, usage_dict
