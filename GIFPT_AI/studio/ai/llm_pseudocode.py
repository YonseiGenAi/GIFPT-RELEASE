# ai/llm_pseudocode.py
import os, json
from openai import OpenAI
from dotenv import load_dotenv

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
    """
    자연어 설명을 도메인과 무관한 순수 pseudocode IR로 변환한다.
    이 단계에서는 domain을 붙이지 않는다.
    """
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

    # metadata는 최소한 항상 존재하게만 해준다.
    result.setdefault("metadata", {})

    return result


# New: variant that also returns token usage

def _extract_usage(usage_obj):
    if not usage_obj:
        return None
    # Support both Chat Completions usage (prompt/completion/total)
    # and potential input/output tokens naming
    pt = getattr(usage_obj, "prompt_tokens", None)
    ct = getattr(usage_obj, "completion_tokens", None)
    tt = getattr(usage_obj, "total_tokens", None)
    if pt is None:
        pt = getattr(usage_obj, "input_tokens", None)
    if ct is None:
        ct = getattr(usage_obj, "output_tokens", None)
    if tt is None and pt is not None and ct is not None:
        tt = pt + ct
    return {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": tt}


def call_llm_pseudocode_ir_with_usage(user_text: str):
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
    result.setdefault("metadata", {})
    usage_dict = _extract_usage(getattr(resp, "usage", None))
    return result, usage_dict





