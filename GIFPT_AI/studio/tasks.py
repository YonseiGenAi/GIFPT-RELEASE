# studio/tasks.py
import os
import time
import requests
from celery import shared_task

from openai import OpenAI
import httpx

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SPRING_CALLBACK_BASE = os.getenv("SPRING_CALLBACK_BASE", "")

# (선택) 프록시/게이트웨이 지원: 환경변수에 있으면 자동 적용
HTTP_PROXY  = os.getenv("HTTP_PROXY")
HTTPS_PROXY = os.getenv("HTTPS_PROXY")
BASE_URL    = os.getenv("OPENAI_BASE_URL")  # 호환 게이트웨이 쓰면 지정

client = None
if OPENAI_API_KEY:
    http_client = None
    if HTTP_PROXY or HTTPS_PROXY:
        http_client = httpx.Client(
            proxies={
                "http://": HTTP_PROXY or "",
                "https://": HTTPS_PROXY or "",
            },
            timeout=60,
            trust_env=True,   # 컨테이너에 남은 프록시 env도 존중
        )
    # http_client가 없으면 기본 클라이언트
    client = OpenAI(api_key=OPENAI_API_KEY, http_client=http_client, base_url=BASE_URL)

@shared_task(name="studio.analyze_pdf_prompt")
def analyze_pdf_prompt(job_id: str, file_path: str, prompt: str):
    """
    PDF + Prompt → GIF/MP4 생성 (현재는 요약 더미/간단 LLM 호출)
    """
    try:
        time.sleep(1.0)

        if client is None:
            summary = f"[DUMMY] file={file_path}, prompt={prompt[:80]}..."
            tokens_used = 0
        else:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.2,
                messages=[
                    {"role": "system", "content": "You summarize PDFs and propose short GIF/MP4 visualization ideas."},
                    {"role": "user", "content": f"Summarize '{file_path}' (assume it's readable) and propose a short GIF/MP4 visualization.\nUser prompt: {prompt}"},
                ],
            )
            summary = resp.choices[0].message.content
            tokens_used = getattr(getattr(resp, "usage", None), "total_tokens", 0) or 0

        # 결과 파일 경로(실제 생성 파이프라인 붙기 전 임시값)
        result_path = f"generated/{job_id}.mp4"
        result = {"summary": summary, "result_path": result_path, "tokens_used": tokens_used}

        # 스프링 콜백
        if SPRING_CALLBACK_BASE:
            try:
                cb = f"{SPRING_CALLBACK_BASE}/api/v1/analysis/{job_id}/complete"
                requests.post(cb, json={"status": "DONE", "result": result}, timeout=5)
            except Exception as e:
                result["callback_error"] = str(e)

        return result

    except Exception as e:
        if SPRING_CALLBACK_BASE:
            try:
                cb = f"{SPRING_CALLBACK_BASE}/api/v1/analysis/{job_id}/complete"
                requests.post(cb, json={"status": "FAILED", "error": str(e)}, timeout=5)
            except:
                pass
        raise
