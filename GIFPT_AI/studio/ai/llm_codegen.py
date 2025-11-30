# ai/llm_codegen.py
import os, json
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BASE_DIR = Path(__file__).resolve().parent

# 같은 폴더에 있는 render_cnn_matrix.py 를 참조
REFERENCE_PATH = BASE_DIR / "render_cnn_matrix.py"

with open(REFERENCE_PATH, "r", encoding="utf-8") as f:
    CNN_REFERENCE = f.read()

SYSTEM_PROMPT = f"""
You are a Manim code generator.
You will receive a structured animation IR (entities, layout, actions)
and must produce a complete, executable Python script using Manim.

Below is a **reference example** of excellent Manim code style
(from render_cnn_matrix). Follow this level of structure, clarity, and animation pacing.

<reference_example>
{CNN_REFERENCE}
</reference_example>

IMPORTANT RULES:
- Always include: `from manim import *`
- Use Manim's color constants (e.g., BLUE_B, YELLOW_C) instead of hex strings.
- NEVER compare color objects or convert them to strings.
- If you need a custom color, write: `color="#abcdef"`, not `hex2color()`.
- Avoid helper functions that redefine color or gradient handling.
- Do NOT use `Group()` at all. Use only `VGroup` for grouping.
- Never pass a `Group`, `Scene`, or other non-VMobject into `VGroup`.
  Every child of `VGroup` must be a VMobject such as `Square`, `Circle`,
  `Rectangle`, `Line`, `Arrow`, `Text`, `MathTex`, `VGroup`, etc.


Style rules you MUST follow:
1. Must start with 'from manim import *'.
2. Define a class named AlgorithmScene(Scene) with construct(self).
3. Use same object naming conventions as the reference (Square, Text, SurroundingRectangle, etc.).
4. Use consistent color palette (BLUE_B, YELLOW_B, PURPLE_B, etc.).
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

Requirements:
1. **Must visualize every operation sequentially** — no skipping.
   - Each "step" in the IR should clearly appear on screen.
   - If the IR defines queues or caches, show items moving IN, OUT, and being REINSERTED.
   - Eviction should visually remove an element, and reinsertion should show it added back.
2. Use readable layout positions and colors provided in the IR.
3. Label each main object (e.g., "S-FIFO", "M-FIFO") above its rectangle.
4. Add subtle pauses (`self.wait(0.3)`) between major steps for clarity.
5. End with a short fade-out of all objects (to signal completion).

Output:
- Write **only Python code** that defines one Manim Scene class (e.g., `class AlgorithmScene(Scene)`).
- Do not include markdown (no ```python or ```).
- Code must be directly executable by `manim`.
"""



def call_llm_codegen(anim_ir: dict):
    prompt = build_prompt_codegen(anim_ir)
    resp = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    code = resp.choices[0].message.content

    code = code.replace("```python", "").replace("```", "").strip()
    return code
