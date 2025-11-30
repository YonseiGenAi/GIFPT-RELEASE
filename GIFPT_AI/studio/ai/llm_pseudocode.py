# app/llm_pseudocode.py
import os, json
from openai import OpenAI
from dotenv import load_dotenv
from app.llm_domain import call_llm_detect_domain

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT_PSEUDOCODE = """
You are an algorithm reasoning engine.
Convert any natural language description of a process or algorithm into
a fine-grained, sequential pseudocode JSON representation.

Your output must be ONLY JSON with these fields:
- metadata: { title (string, optional) }
- entities: list of objects with { id, type, (optional) shape or attributes }
- operations: ordered list of { step (int), subject (string), action (string), target (string, optional), description (string, optional) }


Guidelines:
- Each step must represent a *visualizable action* (create, move, connect, compute, highlight, fade).
- Avoid skipping transitions — break them into multiple substeps if needed.
- Prefer explicit spatial or causal verbs (e.g., "move kernel right", "highlight feature_map", "fade out input").
- Never include None or undefined entities.


DO NOT infer or output "domain" here.
The caller will attach metadata.domain separately.

Be concise, but ensure every operation step is explicit and sequential.
---

Example Input:
"A 2D input matrix is padded with zeros and a kernel slides across it performing convolution.
Each result is stored in a feature map, followed by ReLU activation, max pooling, flatten,
a fully connected layer, and finally a softmax that highlights the highest probability."

Example Output:
{
  "metadata": { "title": "CNN Forward Visualization" },
  "entities": [
    {"id": "input_matrix", "type": "matrix", "attributes": {"padding": 1}},
    {"id": "kernel", "type": "filter", "attributes": {"size": 3}},
    {"id": "feature_map", "type": "matrix"},
    {"id": "relu", "type": "activation"},
    {"id": "pooling", "type": "max_pool"},
    {"id": "dense", "type": "fully_connected"},
    {"id": "softmax", "type": "activation"}
  ],
  "operations": [
    {"step": 1, "subject": "input_matrix", "action": "create", "description": "initialize 2D matrix"},
    {"step": 2, "subject": "input_matrix", "action": "pad", "description": "apply zero padding"},
    {"step": 3, "subject": "kernel", "action": "create", "description": "initialize 3x3 kernel"},
    {"step": 4, "subject": "kernel", "action": "slide_over", "target": "input_matrix", "description": "compute convolution"},
    {"step": 5, "subject": "feature_map", "action": "update", "description": "store convolution result"},
    {"step": 6, "subject": "relu", "action": "apply", "target": "feature_map"},
    {"step": 7, "subject": "pooling", "action": "apply", "target": "feature_map"},
    {"step": 8, "subject": "dense", "action": "connect", "target": "pooling"},
    {"step": 9, "subject": "softmax", "action": "highlight_max", "target": "dense"}
  ]
}
---
Now convert the following text to JSON pseudocode:
"""



def build_prompt_pseudocode(user_text: str) -> str:
    return f"""
Text to convert:
{user_text}

Output JSON strictly matching the schema described above.
""".strip()

def call_llm_pseudocode_ir(user_text: str):
    domain = call_llm_detect_domain(user_text)

    prompt = build_prompt_pseudocode(user_text)
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_PSEUDOCODE},
            {"role": "user", "content": prompt},
        ],
    )
    result = json.loads(resp.choices[0].message.content)

    meta = result.setdefault("metadata", {})
    meta["domain"] = domain

    return result


# --- 2) sorting 전용 trace 생성 ---

SYSTEM_PROMPT_SORTING_TRACE = """
You are a sorting algorithm visual trace generator.

Given a natural language description of sorting, like:
"배열 [5, 1, 4, 2, 8]을 버블 정렬로 오름차순 정렬하는 과정을 단계별로 시각화해줘."

Output JSON with the following structure:

{
  "algorithm": "bubble_sort",
  "input": { "array": [5, 1, 4, 2, 8] },
  "trace": [
    { "step": 1,  "compare": [0,1], "swap": true,  "array": [1,5,4,2,8] },
    { "step": 2,  "compare": [1,2], "swap": true,  "array": [1,4,5,2,8] },
    { "step": 3,  "compare": [2,3], "swap": true,  "array": [1,4,2,5,8] },
    { "step": 4,  "compare": [3,4], "swap": false, "array": [1,4,2,5,8] },

    { "step": 5,  "compare": [0,1], "swap": false, "array": [1,4,2,5,8] },
    { "step": 6,  "compare": [1,2], "swap": true,  "array": [1,2,4,5,8] },
    { "step": 7,  "compare": [2,3], "swap": false, "array": [1,2,4,5,8] },
    { "step": 8,  "compare": [3,4], "swap": false, "array": [1,2,4,5,8] },

    { "step": 9,  "compare": [0,1], "swap": false, "array": [1,2,4,5,8] },
    { "step": 10, "compare": [1,2], "swap": false, "array": [1,2,4,5,8] },
    { "step": 11, "compare": [2,3], "swap": false, "array": [1,2,4,5,8] },
    { "step": 12, "compare": [3,4], "swap": false, "array": [1,2,4,5,8] }
  ]
}

Rules:
- "input.array" MUST be an integer list.
- "trace" MUST be a list of steps in chronological order.
- Each step MUST have:
  - "step": integer
  - "compare": [i, j] indices being compared
  - "swap": boolean
- ONLY output valid JSON. No explanations, no comments.
"""

def _build_prompt_sort_trace(user_text: str) -> str:
    return f"""
User description:
{user_text}

Extract the array and generate a full bubble-sort-like trace.
Output JSON with keys: algorithm, input.array, trace[{{step, compare, swap}}].
""".strip()

def call_llm_sort_trace(user_text: str) -> dict:
    resp = client.chat.completions.create(
        model="gpt-5",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_SORTING_TRACE},
            {"role": "user", "content": _build_prompt_sort_trace(user_text)},
        ],
    )
    return json.loads(resp.choices[0].message.content)

