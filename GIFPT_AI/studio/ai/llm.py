# app/llm.py
import os, json
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv
from openai import OpenAI
from app.schema import schema_errors, invariants_errors  # 검증은 기존 함수 재사용:contentReference[oaicite:2]{index=2}
from app.prompts import DOMAIN_PROMPTS

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------- Stage 1: 이해·예시·trace ----------
STAGE1_SYSTEM = """You are an algorithm explainer. Output ONLY JSON."""

def build_prompt_stage1(user_text: str) -> str:
    return f"""
Explain the algorithm shortly and produce a small concrete example with a step-by-step trace.

Output ONLY JSON with keys:
- algorithm: snake_case (e.g., "bubble_sort")
- description: short summary (Korean allowed)
- input: for sorting, use {{"array":[...]}} with length ≤ 6
- trace: list of steps. Each step:
  - step: integer
  - compare: [i, j]  # indexes compared
  - swap: boolean
  - array: the full array state AFTER this step
- metadata: include {{"domain":"sorting"}}

TEXT:
{user_text}
""".strip()

def call_llm_stage1(user_text: str) -> Dict[str, Any]:
    prompt = build_prompt_stage1(user_text)
    resp = client.chat.completions.create(
        model="gpt-5",  
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": STAGE1_SYSTEM},
                  {"role": "user", "content": prompt}],
    )
    return json.loads(resp.choices[0].message.content)

# ---------- Stage 2: trace → IR ----------
STAGE2_SYSTEM = """You convert a trace JSON into an animation-ready IR. Output ONLY JSON with exactly three top-level keys: components, events, metadata."""


def build_prompt_stage2(explain_json: Dict[str, Any]) -> str:
    return f"""
Convert the following trace JSON into an animation IR.

Rules:
- Output must have three top-level keys: components[], events[], metadata{{}}.
- Make one component per input item: ids "arr0","arr1",... label is current value (string)
- For each trace step:
  - Emit: {{"t": T, "op": "compare", "from": "arr<i>", "to": "arr<j>"}}
  - If swap==true, also emit: {{"t": T+0.2, "op": "swap", "from": "arr<i>", "to": "arr<j>"}}
- Use non-decreasing t (start 0.0, step 0.2)
- metadata.view = "flow"; metadata.domain = input.metadata.domain

TRACE JSON:
{json.dumps(explain_json, ensure_ascii=False)}
"""


def call_llm_stage2(explain_json: Dict[str, Any], temperature: float = 0.0) -> Dict[str, Any]:
    prompt = build_prompt_stage2(explain_json)
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": STAGE2_SYSTEM},
                  {"role": "user", "content": prompt}],
    )
    return json.loads(resp.choices[0].message.content)

# ---------- Validation wrapper ----------
def validate_ir(doc: Dict[str, Any]) -> List[str]:
    """schema + invariants 오류 리스트를 반환 (빈 리스트면 통과)."""
    return schema_errors(doc) + invariants_errors(doc)

def call_llm_json_ir(user_text: str, temperature: float = 0.0):
    """
    [호환용] 옛 함수 이름을 유지하되, 내부적으로
    1) stage1(설명+예시+trace) → 2) stage2(trace→IR) 를 호출해서 IR을 만든다.
    기존 호출부가 (dict, raw_str) 를 기대하므로 그대로 반환.
    """
    explain = call_llm_stage1(user_text, temperature=temperature)
    ir = call_llm_stage2(explain, temperature=temperature)
    raw = json.dumps(ir, ensure_ascii=False)
    return ir, raw

def generate_ir_with_validation(user_text: str, max_retries_zero_temp: int = 2) -> Dict[str, Any]:
    """
    1) temp=0으로 시도 → 검증 실패 시 피드백 첨부 재시도
    2) 그래도 실패하면 temp=0.3으로 한 번 더
    """
    feedback = ""
    for attempt in range(max_retries_zero_temp + 1):
        doc, raw = call_llm_json_ir(user_text + ("\n\n" + feedback if feedback else ""), temperature=0.0)
        errs = schema_errors(doc) + invariants_errors(doc)
        if not errs:
            return doc
        # 구체적 피드백 생성
        bullets = "\n".join(f"- {e}" for e in errs)
        feedback = f"Correct these issues:\n{bullets}\nReturn valid JSON only."

    # fallback: temperature 높여서 다양성 확보
    doc, raw = call_llm_json_ir(user_text + ("\n\n" + feedback if feedback else ""), temperature=0.3)
    errs = schema_errors(doc) + invariants_errors(doc)
    if errs:
        raise ValueError("LLM JSON IR generation failed:\n" + "\n".join(errs))
    return doc

# ---------- Domain-level IR Generator ----------
def call_llm_domain_ir(domain: str, user_text: str, temperature: float = 0.0) -> Dict[str, Any]:
    """도메인 이름에 맞는 프롬프트 템플릿을 이용해 IR 생성"""
    if domain not in DOMAIN_PROMPTS:
        raise ValueError(f"Unknown domain: {domain}")

    prompt_cfg = DOMAIN_PROMPTS[domain]
    base_prompt = prompt_cfg["template"].format(text=user_text)

    # ✅ 전 도메인 공통 규칙: 사용자의 수치, 조건, 표현을 절대 변경하지 말 것
    universal_rules = """
    <GLOBAL RULES>
    - 절대로 사용자의 수치값(예: 3x3, 2, stride=1, 0.01, learning rate 등)을 수정하거나 보정하지 말라.
    - padding, stride, kernel_size, input_size, epoch, batch_size, temperature 등
      모든 하이퍼파라미터는 사용자가 언급한 값을 그대로 사용해야 한다.
    - 사용자가 명시하지 않은 값만 기본값으로 채운다.
    - input_size는 padding을 포함하지 않는다. padding은 별도의 값으로만 사용된다.
    - 기본값은 도메인별 상식적인 값으로 설정하되, "추정"하지 않는다. (예: CNN은 stride=1, padding=0, seed=1)
    - 출력 JSON은 오직 요청된 도메인에 필요한 필드만 포함해야 한다.
    - 출력은 항상 완전한 JSON 객체로 반환해야 하며, 문자열이나 설명문이 포함되어서는 안 된다.
    </GLOBAL RULES>
    """

    # ✅ 도메인별 템플릿에 공통 규칙 주입
    full_prompt = base_prompt + "\n\n" + universal_rules

    # ✅ LLM 호출
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": prompt_cfg["system"]},
            {"role": "user", "content": full_prompt},
        ],
    )

    print("\n=== 🧠 LLM RAW OUTPUT ===")
    print(resp.choices[0].message.content)
    print("=========================\n")

    return json.loads(resp.choices[0].message.content)
