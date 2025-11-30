# app/llm_domain.py
import os, json
from openai import OpenAI
from dotenv import load_dotenv
from .llm import call_llm_domain_ir
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
- "hash_table"
- "graph_traversal"
- "dynamic_programming"
- "math"
- "generic"

Classification rules:
- If mentions: convolution, kernels, padding, stride, CNN → "cnn_param"
- If mentions: **sorting algorithm** (bubble sort, selection sort, insertion sort, quicksort, merge sort) and describes **comparison/swap operations** → "sorting"
  * NOTE: Binary search, linear search are NOT sorting → "generic"
  * NOTE: "정렬된 배열" (sorted array) alone is NOT sorting → check if describing sorting algorithm
- If mentions: **complete Transformer architecture** (encoder, decoder, full pipeline, next word prediction) → "transformer"
  * NOTE: If ONLY describing attention mechanism (Q/K/V, attention score, self-attention process) WITHOUT full Transformer → "generic"
  * Example: "self-attention 계산 과정" → "generic", "Transformer로 번역" → "transformer"
- If mentions: cache, FIFO, LRU, queues, eviction, hit/miss → "cache"
- If mentions: hash table, hash map, bucket, chaining, collision, hash function → "hash_table"
- If mentions: BFS, DFS, graph, traversal, queue, stack, visited → "graph_traversal"
- If mentions: binary search, linear search, search algorithm, 이진 탐색, 탐색 과정 → "generic"
- If mentions: dynamic programming, DP, fibonacci, memoization, subproblems → "dynamic_programming"
- If mentions: derivatives, integrals, probability, expectation, variance, matrices → "math"
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

def build_sorting_trace_ir(user_text: str) -> dict:
    """
    정렬 trace는 도메인 템플릿 시스템(domain_ir)을 그대로 사용.
    (sorting_trace 템플릿은 prompts.py에 이미 존재함.)
    """
    return call_llm_domain_ir("sorting_trace", user_text)
