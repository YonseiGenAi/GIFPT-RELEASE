# ai/llm_pattern.py
import os, json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


PATTERN_SYSTEM_PROMPT = """
You are a pattern classifier.
Your task is to decide the VISUALIZATION PATTERN for a computational process.

Allowed patterns:
- "grid"          : 2D matrices/arrays, heatmaps, 2D grids (rows × columns)
                    Examples: matrix operations, 2D DP table, convolution
                    ※ 1D arrays should use "sequence", NOT "grid"
                    
- "sequence"      : 1D arrays, step-by-step algorithms, sorting, searching
                    Examples: array sorting, binary search, queue/stack operations
                    ※ Use for sequential/iterative processes on 1D arrays
                    
- "seq_attention" : Tokens + attention weights (transformer-style)
                    Examples: showing how tokens attend to each other
                    
- "flow"          : Pipelines, stages, dataflow, processing chains
                    Examples: ML pipeline (Input→Preprocess→Train→Output)

**Decision Rules:**
1. Is it a 2D structure (rows × columns)? → "grid"
2. Is it operating on a 1D array (sorting, searching, etc.)? → "sequence"
3. Does it show ML pipeline stages? → "flow"
4. Does it involve attention between tokens? → "seq_attention"

Return ONLY JSON: {"pattern": "<one_of_above>"} 
"""


def call_llm_pattern(user_text: str) -> str:
    """Ask the LLM to *recommend* a pattern."""
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": PATTERN_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Text:\n'''{user_text}'''\nReturn only JSON.",
            },
        ],
    )
    data = json.loads(resp.choices[0].message.content)
    return data.get("pattern", "flow")  # fallback to flow

