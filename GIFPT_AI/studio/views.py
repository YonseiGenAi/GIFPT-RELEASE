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
    # 1) raw body / request.data 찍어 보기
    try:
        raw_body = request.body.decode("utf-8")
    except Exception:
        raw_body = "<decode error>"

    logger.info(f"[analyze] raw_body = {raw_body!r}")
    logger.info(f"[analyze] request.data = {request.data}")

    # 2) DRF가 파싱한 data 먼저 사용
    data = request.data

    # 3) data가 비어 있으면 raw_body에서 JSON 파싱 재시도
    if not data:
        try:
            if raw_body.strip():
                data = json.loads(raw_body)
            else:
                data = {}
        except Exception as e:
            logger.error(f"[analyze] json.loads 실패: {e}")
            data = {}

    logger.info(f"[analyze] 최종 data = {data}")

    # 4) 필수 필드 체크 (여기서 뭐가 들어오는지 먼저 확인)
    missing = [k for k in ("job_id", "file_path", "prompt") if k not in data]
    if missing:
        # 🔥 일단 여기서 바로 400을 주되, data를 그대로 응답해서 Spring 로그에서 볼 수 있게
        return Response(
            {
                "error": "missing_fields",
                "missing": missing,
                "received_data": data,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 5) 이제 Serializer에 한 번 더 태워보기 (정상 흐름)
    ser = AnalyzeRequestSerializer(data=data)
    ser.is_valid(raise_exception=True)

    task = analyze_pdf_prompt.delay(**ser.validated_data)
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
