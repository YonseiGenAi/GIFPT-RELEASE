#studio/tasks.py
import os, time, requests
from celery import shared_task
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SPRING_CALLBACK_BASE = os.getenv("SPRING_CALLBACK_BASE")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

@shared_task(name='studio.analyze_pdf_prompt')
def analyze_pdf_prompt(job_id: str, file_path: str, prompt: str):
    """
    PDF + Prompt → GIF/MP4 생성 (현재는 GPT 더미)
    """
    try:
        time.sleep(1.0)

        if client is None:
            summary = f"[DUMMY] file={file_path}, prompt={prompt[:60]}..."
            tokens_used = 0
        else:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.2,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes PDFs and proposes animation ideas."},
                    {"role": "user", "content": f"Summarize the PDF at '{file_path}' and propose a short GIF/MP4 visualization.\nUser prompt: {prompt}"}
                ]
            )
            summary = completion.choices[0].message.content
            tokens_used = getattr(getattr(completion, "usage", None), "total_tokens", 0)

        result_path = f"generated/{job_id}.mp4"
        result = {"summary": summary, "result_path": result_path, "tokens_used": tokens_used}

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