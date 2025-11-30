# app/llm_anim_ir.py
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
- layout: list of { id, shape, position: [x, y], color (optional) }
- actions: list of { step, target, animation, description }

Guidelines:
- Use domain to infer typical layout:
  - cache: S-FIFO, M-FIFO, G aligned vertically
  - cnn_param: matrices left→right (input → fmap → pool)
  - sorting: array elements aligned horizontally
- animation types: "fade_in", "move", "highlight", "swap", "fade_out"
- Coordinates in range [-5, 5]
- Be consistent with pseudocode steps.
- Output valid JSON only."""

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


