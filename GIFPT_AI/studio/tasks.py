# GIFPT_AI/studio/tasks.py

import os
import logging
import requests

from celery import shared_task
from django.conf import settings

from openai import OpenAI
import PyPDF2

logger = logging.getLogger(__name__)

SPRING_CALLBACK_BASE = os.environ.get("SPRING_CALLBACK_BASE", "http://spring:8080")
UPLOAD_DIR = os.environ.get("GIFPT_UPLOAD_DIR", "/data/uploads")
RESULT_DIR = os.environ.get("GIFPT_RESULT_DIR", "/data/results")

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def extract_text_from_pdf(path: str) -> str:
    """간단 PDF 텍스트 추출 헬퍼"""
    text_parts = []
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n\n".join(text_parts)


@shared_task(name="studio.analyze_pdf_prompt")
def analyze_pdf_prompt(job_id: int, input_path: str, user_prompt: str):
    """
    - jobId, pdf 경로, 사용자 프롬프트를 받아서
    - PDF 텍스트 추출
    - OpenAI로 핵심 요약 생성
    - (TODO) 알고리즘 시각화 파이프라인 실행 → 영상 파일 생성
    - Spring /api/v1/analysis/{jobId}/complete 로 콜백
    """
    logger.info("analyze_pdf_prompt started job_id=%s input_path=%s", job_id, input_path)

    # input_path가 절대경로가 아니면 UPLOAD_DIR 기준으로 합쳐줌
    if not os.path.isabs(input_path):
        pdf_path = os.path.join(UPLOAD_DIR, input_path)
    else:
        pdf_path = input_path

    try:
        # 1) PDF 텍스트 추출
        pdf_text = extract_text_from_pdf(pdf_path)

        # 2) OpenAI로 핵심 요약 생성
        system_prompt = ("""
            너는 알고리즘/코드/수학 내용을 교육용으로 정리하는 어시스턴트다.
            사용자의 프롬프트를 기준으로 PDF 내용을 핵심 알고리즘 흐름 위주로 요약해라.

            <GLOBAL RULES>
            - 절대로 사용자의 수치값(예: 3x3, 2, stride=1, 0.01, learning rate 등)을 수정하거나 보정하지 말라.
            - padding, stride, kernel_size, input_size, epoch, batch_size, temperature 등
            모든 하이퍼파라미터는 사용자가 언급한 값을 그대로 사용해야 한다.
            - 사용자가 명시하지 않은 값만 기본값으로 채운다.
            - 기본값은 도메인별 상식적인 값으로 설정하되, "추정"하지 않는다. 
            (예: CNN은 stride=1, padding=0, seed=1)
            - 사용자가 여러 곳에서 서로 다른 값을 적었다면, 
            반드시 사용자가 제일 마지막에 언급한 값을 우선시한다.
            - 값이 애매하거나 충돌하는 경우, 네가 멋대로 바꾸지 말고
            "user_defined": false 와 함께 "note" 필드에 이유를 적어라.
        """)

        user_content = f"""[사용자 프롬프트]
{user_prompt}

[PDF 내용 일부]
{pdf_text[:12000]}"""

        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        summary = completion.choices[0].message.content or ""

        # 3) (TODO) 알고리즘 시각화 + 영상 생성 파이프라인
        # 여기서 네가 만든 파이프라인을 호출해서 result_abs 에 영상 파일 생성하면 됨.
        # 일단은 "영상이 /data/results 아래에 있다" 정도로만 둔다.
        os.makedirs(RESULT_DIR, exist_ok=True)
        result_rel = f"{job_id}_result.mp4"
        result_abs = os.path.join(RESULT_DIR, result_rel)

        # --- TODO: 실제 파이프라인 결과를 result_abs에 저장 ---
        # run_pipeline(pdf_path, summary, result_abs)
        # ----------------------------------------------------

        # 지금은 S3 아직까지 안 묶었다 치고, Spring이 로컬 경로를 URL로 바꿔줄 수 있게
        # 단순히 상대 경로만 전달 (또는 나중에 S3 URL로 교체)
        result_url = result_rel

        callback_payload = {
            "status": "SUCCESS",
            "resultUrl": result_url,
            "summary": summary,
            "errorMessage": None,
        }

    except Exception as e:
        logger.exception("analyze_pdf_prompt failed job_id=%s", job_id)
        callback_payload = {
            "status": "FAILED",
            "resultUrl": None,
            "summary": None,
            "errorMessage": str(e),
        }

    # 4) Spring 콜백
    try:
        cb_url = f"{SPRING_CALLBACK_BASE}/api/v1/analysis/{job_id}/complete"
        logger.info("calling spring callback %s with %s", cb_url, callback_payload["status"])
        requests.post(cb_url, json=callback_payload, timeout=10)
    except Exception:
        logger.exception("failed to callback spring for job_id=%s", job_id)
