# ai/llm_anim_ir.py
import os, json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an animation structure planner.
Convert a pseudocode JSON into a structured animation representation
that describes what entities to draw, where to place them, and how to animate each step.

Your output must be ONLY JSON with these fields:
- metadata: { domain, title }
- layout: list of { id, shape, position: [x, y], color (optional), label (optional), data (optional), dimensions (optional) }
- actions: list of { step, target, animation, description }

Shape field:
- shape is a free string describing the visual primitive. Prefer standard Manim primitives (Rectangle, Circle, Line, Arrow, Dot, Polygon) or semantic tokens like "matrix", "array".
- If using a non-standard/custom shape, still provide enough context via label/data/dimensions so that downstream renderers can decide how to draw it.

Guidelines for data field:
- If using a "matrix" shape: provide 2D array of values, e.g., "data": [[1,2,3], [4,5,6]]
- If using an "array" shape: provide 1D array of values, e.g., "data": [10, 20, 30, 40]
- For operations: provide formula, e.g., "data": "Q·K^T / √d_k"
- Add "dimensions" for size labels, e.g., "dimensions": "3×3" or "dimensions": "(seq_len, d_model)"

Guidelines for labels:
- Add "label" field for identifiers (e.g., "Input", "Q", "K", "V", "Attention Scores")
- Skip "label" field for purely decorative elements

Guidelines by domain:
- cache: S-FIFO, M-FIFO queues with item values shown
- cnn_param: matrices with actual values/dimensions (3×3 kernel, 4×4 input, etc.)
- sorting: array with values to be sorted [5, 2, 8, 1, 9]
- attention: Q, K, V matrices with dimensions shown, attention scores as heatmap
- dynamic_programming: DP table as matrix with computed values

Animation types: "fade_in", "move", "highlight", "swap", "fade_out"
Coordinates in range [-5, 5]
Output valid JSON only.

Example output:
{
  "metadata": {"domain": "cnn_param", "title": "CNN Convolution"},
  "layout": [
    {"id": "input", "shape": "matrix", "position": [-4, 0], "color": "blue", 
     "label": "Input", "data": [[1,2,3,4], [5,6,7,8], [9,10,11,12], [13,14,15,16]], "dimensions": "4×4"},
    {"id": "kernel", "shape": "matrix", "position": [0, 0], "color": "red", 
     "label": "Kernel", "data": [[1,0,-1], [1,0,-1], [1,0,-1]], "dimensions": "3×3"},
    {"id": "output", "shape": "matrix", "position": [4, 0], "color": "green", 
     "label": "Output", "dimensions": "2×2"}
  ],
  "actions": [
    {"step": 1, "target": "input", "animation": "fade_in", "description": "Show input matrix"},
    {"step": 2, "target": "kernel", "animation": "fade_in", "description": "Show convolution kernel"}
  ]
}
"""

def build_prompt_anim_ir(pseudocode_json: dict) -> str:
    return f"""
Convert the following pseudocode into a structured animation plan JSON:

{json.dumps(pseudocode_json, ensure_ascii=False, indent=2)}
"""

def call_llm_anim_ir(pseudocode_json: dict):
    prompt = build_prompt_anim_ir(pseudocode_json)
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return json.loads(resp.choices[0].message.content)

def call_llm_anim_ir_with_usage(pseudocode_json: dict):
    prompt = build_prompt_anim_ir(pseudocode_json)
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    result = json.loads(resp.choices[0].message.content)
    usage = getattr(resp, "usage", None)
    if usage:
        # OpenAI SDK v1 returns attributes; keep fallback for dict-like
        usage_dict = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None) or (usage.get("prompt_tokens") if hasattr(usage, "get") else None),
            "completion_tokens": getattr(usage, "completion_tokens", None) or (usage.get("completion_tokens") if hasattr(usage, "get") else None),
            "total_tokens": getattr(usage, "total_tokens", None) or (usage.get("total_tokens") if hasattr(usage, "get") else None),
        }
    else:
        usage_dict = None
    return result, usage_dict
    