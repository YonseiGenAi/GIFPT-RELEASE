# studio/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
from django.conf import settings
import os
import json
import logging

from .serializers import AnalyzeRequestSerializer, ChatRequestSerializer
from .tasks import analyze_pdf_prompt
from GIFPT_AI.celery import app as celery_app

logger = logging.getLogger(__name__)

def get_openai_client():
    """환경변수 기반으로 OpenAI 클라이언트를 지연 생성."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    # import를 함수 내부로 옮겨 버전/시그니처 이슈가 있어도 전역 크래시 방지
    from openai import OpenAI
    # proxies 인자는 절대 전달하지 말고, 필요 시 컨테이너 env(HTTP[S]_PROXY)로 처리
    return OpenAI(api_key=api_key)

@api_view(['POST'])
def analyze(request):
    # 1) 들어온 요청 상태를 싹 다 찍어보자
    logger.error("🔥 [Django] /analyze called")
    logger.error("🔥 RAW BODY = %r", request.body)
    logger.error("🔥 CONTENT_TYPE = %s", request.content_type)
    logger.error("🔥 DRF PARSED DATA (request.data) = %s", getattr(request, "data", None))

    # 2) 우선 DRF가 파싱한 데이터 사용
    data = getattr(request, "data", {}) or {}

    # 3) 만약 비어 있으면 raw body를 직접 JSON으로 파싱 시도
    if not data:
        try:
            raw = request.body.decode("utf-8") if request.body else ""
            logger.error("🔥 Trying manual json.loads from raw body: %r", raw)
            if raw:
                data = json.loads(raw)
                logger.error("🔥 Manual parsed data = %s", data)
        except Exception as e:
            logger.error("🔥 Manual JSON parse failed: %s", e)

    required = ["job_id", "file_path", "prompt"]
    missing = [f for f in required if f not in data]

    if missing:
        logger.error("🔥 Missing fields: %s, received_data=%s", missing, data)
        return Response(
            {
                "error": "missing_fields",
                "missing": missing,
                "received_data": data,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 4) 여기까지 왔으면 정상적으로 값이 들어온 것
    task = analyze_pdf_prompt.delay(
        job_id=data["job_id"],
        file_path=data["file_path"],
        prompt=data["prompt"],
    )
    return Response({"task_id": task.id, "status": "QUEUED"}, status=status.HTTP_202_ACCEPTED)

@api_view(['GET'])
def task_status(request, task_id: str):
    res = AsyncResult(task_id, app=celery_app)
    payload = {"task_id": task_id, "state": res.state}
    if res.state == "SUCCESS":
        payload["result"] = res.result
    elif res.state == "FAILURE":
        payload["error"] = str(res.result)
    return Response(payload)

@api_view(['POST'])
def chat(request):
    ser = ChatRequestSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    system_prompt = "You are a helpful tutor that explains GIF/MP4-based educational content."
    if data.get("file_path"):
        system_prompt += f" The related media is located at: {data['file_path']}."
    if data.get("summary"):
        system_prompt += f" Here is a short summary: {data['summary']}."

    messages = [{"role": "system", "content": system_prompt}] + data["messages"]

    client = get_openai_client()
    if client is None:
        last_user = next((m["content"] for m in reversed(data["messages"]) if m["role"] == "user"), "")
        return Response({"reply": f"[DUMMY] 질문: {last_user[:80]}...", "session_id": data.get("session_id", "")})

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=messages,
        )
        reply = completion.choices[0].message.content
        return Response({"reply": reply, "session_id": data.get("session_id", "")})
    except Exception as e:
        # 모델/네트워크 오류 시에도 서버가 죽지 않도록 방어
        return Response(
            {"reply": f"[ERROR] OpenAI 호출 실패: {e}", "session_id": data.get("session_id", "")},
            status=status.HTTP_502_BAD_GATEWAY,
        )
