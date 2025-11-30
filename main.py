# app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

from app.llm_domain import call_llm_detect_domain
from app.llm import call_llm_domain_ir
from app.render_cnn_matrix import render_cnn_matrix
from app.llm_pseudocode import call_llm_pseudocode_ir, call_llm_sort_trace
from app.llm_anim_ir import call_llm_anim_ir
from app.llm_codegen import call_llm_codegen
from app.render_sorting import render_sorting

import tempfile
import subprocess
import re
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()


# --------- 요청 스키마 ---------
class GenerateRequest(BaseModel):
    text: str
    domain_hint: Optional[str] = None


# --------- 공통 유틸 ---------
def sanitize_text(text: str) -> str:
    # 줄바꿈/공백 정리 정도만
    text = re.sub(r"\s+", " ", text)
    return text.strip()


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# --------- 단일 엔드포인트 ---------
@app.post("/generate")
async def generate(req: GenerateRequest):
    """
    텍스트 한 번 보내면 도메인 자동 감지해서
    - cnn_param  → CNN 파라미터 시각화
    - sorting    → 정렬 trace + 정렬 전용 renderer
    - 기타       → pseudocode IR → animation IR → LLM Manim 코드 → manim 실행
    """
    user_text = sanitize_text(req.text)

    # 1) 도메인 결정 (hint 있으면 우선, 없으면 LLM)
    if req.domain_hint:
        domain = req.domain_hint
    else:
        domain = call_llm_detect_domain(user_text)

    # 2) 도메인별 처리 -----------------------------

    # (1) CNN 파라미터 전용
    if domain == "cnn_param":
        ir = call_llm_domain_ir("cnn_param", user_text)
        params = ir["ir"]["params"]
        video_path = render_cnn_matrix(params)
        return {
            "domain": domain,
            "ir": ir,
            "video_path": video_path,
        }

    # (2) 정렬 전용 파이프라인 (trace → render_sorting)
    elif domain == "sorting":
        sort_trace = call_llm_sort_trace(user_text)
        video_path = render_sorting(sort_trace)
        return {
            "domain": domain,
            "trace": sort_trace,
            "video_path": video_path,
        }

    # (3) 일반 알고리즘/모델 시각화 (pseudocode → anim_ir → manim 코드)
    else:
        pseudo_ir = call_llm_pseudocode_ir(user_text)
        anim_ir = call_llm_anim_ir(pseudo_ir)
        manim_code = call_llm_codegen(anim_ir)

        # manim 코드 임시 파일로 저장 후 실행
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(manim_code)
            tmp_path = tmp.name

        subprocess.run(
            ["manim", "-ql", tmp_path, "AlgorithmScene", "--format", "mp4"],
            check=True,
        )

        return {
            "pseudocode_ir": pseudo_ir,
            "anim_ir": anim_ir,
            "domain": domain,
            "message": "🎬 Visualization generation started successfully!",
        }
