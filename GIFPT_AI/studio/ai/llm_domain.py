# app/llm_domain.py
import os, json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DOMAIN_SYSTEM_PROMPT = """
You are a strict domain classifier for algorithm / AI descriptions.

You MUST output ONLY JSON of the form:
{"domain": "<one_of_allowed>"}

Allowed domains:
- "cnn_param"
- "sorting"
- "transformer"
- "cache"
- "math"
- "generic"

Classification rules:
- If the text mentions convolution, kernels, padding, stride, CNN → "cnn_param"
- If the text mentions sorting, array, bubble sort, selection sort, insertion sort, quicksort → "sorting"
- If the text mentions Transformer, self-attention, Query/Key/Value, attention heads → "transformer"
- If the text mentions cache, FIFO, LRU, queues, eviction → "cache"
- If the text mentions derivatives, integrals, probability, expectation, variance, matrices → "math"
- Otherwise → "generic"

Return ONLY JSON. No extra text, no comments.
"""

def call_llm_detect_domain(user_text: str) -> str:
    """LLM이 사용자 입력을 보고 도메인만 분류하게 하는 전용 함수."""
    prompt = f'Text:\n"""\n{user_text}\n"""\n\nReturn JSON with the "domain" field only.'
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": DOMAIN_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    data = json.loads(resp.choices[0].message.content)
    domain = data.get("domain", "generic")
    return domain
