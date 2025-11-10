from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
from django.conf import settings
from openai import OpenAI
import os

from .serializers import AnalyzeRequestSerializer, ChatRequestSerializer
from .tasks import analyze_pdf_prompt
from gifpt_ai.celery import app as celery_app

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

@api_view(['POST'])
def analyze(request):
    ser = AnalyzeRequestSerializer(data=request.data)
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

    if client is None:
        last_user = next((m["content"] for m in reversed(data["messages"]) if m["role"] == "user"), "")
        return Response({"reply": f"[DUMMY] 질문: {last_user[:80]}...", "session_id": data.get("session_id", "")})

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=messages
    )
    reply = completion.choices[0].message.content
    return Response({"reply": reply, "session_id": data.get("session_id", "")})
