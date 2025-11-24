# studio/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
from django.conf import settings
import os
import json

from .serializers import AnalyzeRequestSerializer, ChatRequestSerializer
from .tasks import analyze_pdf_prompt
from GIFPT_AI.celery import app as celery_app

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
    """
    Spring에서 오는 JSON이 content-type 때문에 DRF가 제대로 파싱 못 하는 경우를 대비해서
    request.data가 비어 있으면 request.body로 한 번 더 JSON 파싱 시도.
    """
    # 🔥 1차 시도: DRF가 파싱한 data
    data = request.data

    # 디버깅용 로그 (원하면 잠깐 넣어도 됨)
    # print("DEBUG analyze request.data =", data)

    # 🔥 만약 data가 비어있으면, raw body로 직접 JSON 파싱 시도
    if not data:
        try:
            raw = request.body.decode("utf-8")
            if raw.strip():
                data = json.loads(raw)
            else:
                data = {}
        except Exception as e:
            # JSON 파싱 실패하면 그냥 빈 dict
            data = {}

    # 🔥 이제 이 data를 가지고 serializer 검증
    ser = AnalyzeRequestSerializer(data=data)
    ser.is_valid(raise_exception=True)

    # Celery task 호출
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
