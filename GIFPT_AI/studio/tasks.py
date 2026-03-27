# GIFPT_AI/studio/tasks_vision.py

import hashlib
import os
import logging
import requests
import base64
import json
from io import BytesIO
from pathlib import Path
from typing import Optional
import time

import boto3
from celery import shared_task
from django.conf import settings
from studio.video_render import render_video_from_instructions, run_manim_code, RESULT_DIR
from studio.s3_utils import upload_to_s3, S3_BUCKET, S3_REGION

from openai import OpenAI
import fitz  # PyMuPDF
from PIL import Image

logger = logging.getLogger(__name__)

SPRING_CALLBACK_BASE = os.environ.get("SPRING_CALLBACK_BASE", "http://spring:8080")
UPLOAD_DIR = os.environ.get("GIFPT_UPLOAD_DIR", "/data/uploads")
RESULT_DIR = os.environ.get("GIFPT_RESULT_DIR", "/data/results")

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def pdf_to_base64_images(pdf_path):
    """
    Convert PDF pages to base64 encoded images using PyMuPDF.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        list: List of base64 encoded images
    """
    try:
        logger.info(f"Converting PDF pages to images: {pdf_path}")
        doc = fitz.open(pdf_path)
        
        base64_images = []
        for page_num in range(len(doc)):
            logger.info(f"Processing page {page_num + 1}/{len(doc)}")
            page = doc[page_num]
            
            # Render page to an image (pixmap)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
            
            # Convert pixmap to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Convert PIL Image to base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            base64_images.append(img_base64)
        
        doc.close()
        return base64_images
    
    except Exception as e:
        logger.error(f"Error converting PDF: {str(e)}")
        return None


def generate_summary_from_images(base64_images, user_prompt=None):
    """
    Generate a summary from PDF images using OpenAI's vision model.
    
    Args:
        base64_images (list): List of base64 encoded images
        user_prompt (str): Optional user prompt with constraints for video generation
        
    Returns:
        dict: Contains 'summary' and 'video_instructions'
    """
    try:
        example_output = """Dijkstras algorithm is a method for finding the shortest path from a starting node to all other nodes in a weighted graph with non negative edge weights. It keeps track of the shortest known distance to each node and repeatedly selects the unvisited node with the smallest distance so far. From that node it relaxes each outgoing edge, meaning it checks whether going through that node gives a shorter route to its neighbors and updates their distances if so. This process continues until all nodes have been visited or all reachable nodes have their shortest distances finalized. For an example, imagine starting at node A in a graph where A connects to B with weight 4 and to C with weight 2. First set the distance to A as 0 and all others as infinity. The closest unvisited node is A, so visit it and update B to distance 4 and C to distance 2. Next the closest unvisited node is C with distance 2. From C, suppose there is an edge to D with weight 3. The new possible distance to D is 2 plus 3 equals 5, so set D to 5. Now the closest unvisited node is B with distance 4; if B connects to D with weight 1 then the new possible distance to D is 4 plus 1 equals 5, which does not improve on the current 5. Finally visit D with distance 5. The algorithm ends with the shortest distances from A to the other nodes recorded as 4 for B, 2 for C, and 5 for D. Create a video showing Dijkstra's algorithm with the nodes A, B, C, and D with weights 4, 2, and 3."""
        
        example_user_prompt = "Use the nodes A, B, C, and D with weights 4, 2, and 3 as described."
        
        # Build the prompt based on whether user provided constraints
        if user_prompt:
            prompt_text = f"""Analyze the content in these PDF pages and create a summary with video instructions.

First, write the summary in this EXACT format - two continuous parts in one flowing text with no line breaks:
1. First part: Explain the key logic or main concept
2. Second part: Provide a concrete example starting with "For an example"

Here's a reference example of the EXACT format to follow:
{example_output}

Then, provide detailed instructions for generating a video visualization, incorporating these user constraints: {user_prompt}

USER CONSTRAINTS RULES:
- NEVER modify user's numerical values (stride, padding, kernel_size, learning_rate, epoch, batch_size, etc.)
- Use user's values EXACTLY as mentioned
- Only fill in defaults for parameters the user didn't specify
- If user mentions conflicting values, use the LAST mentioned value
- If values are ambiguous, note it in the video_instructions

Example user prompt: "{example_user_prompt}"

Return your response in JSON format:
{{"summary": "continuous text with logic and example...", "video_instructions": "Create a video showing... using stride=2 (user-specified), padding=0 (default)..."}}"""
        else:
            prompt_text = f"""Analyze the content in these PDF pages and create a summary with video instructions.

    First, write the summary in this EXACT format - two continuous parts in one flowing text with no line breaks:
1. First part: Explain the key logic or main concept
2. Second part: Provide a concrete example starting with "For an example"

Here's a reference example of the EXACT format to follow:
{example_output}

Then, provide detailed instructions for generating a video visualization of the main logic.

Return your response in JSON format:
{{"summary": "continuous text with logic and example...", "video_instructions": "Create a video showing..."}}"""
        
        # Build content array with all images
        content = [
            {
                "type": "text",
                "text": prompt_text
            }
        ]
        
        # Add all images to the content
        for img_base64 in base64_images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_base64}"
                }
            })
        
        logger.info(f"Generating AI analysis from {len(base64_images)} page(s)")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing algorithms and educational content. You generate JSON output with 'summary' (continuous text combining logic explanation and example with no line breaks) and 'video_instructions'. The summary must be one continuous flowing text."
                },
                {
                    "role": "user",
                    "content": content
                }
            ],
            temperature=0.7,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content.strip())
        
        # Remove all newlines from all fields to ensure completely continuous text
        if 'summary' in result:
            result['summary'] = result['summary'].replace('\n', ' ').strip()
        if 'video_instructions' in result:
            result['video_instructions'] = result['video_instructions'].replace('\n', ' ').strip()
        # 🔥 DEBUG LOG — Print summary + instructions
        logger.info("==== OpenAI Summary BEGIN ====")
        logger.info(result.get("summary", "NO SUMMARY"))
        logger.info("==== OpenAI Summary END ====")

        logger.info("==== OpenAI Video Instructions BEGIN ====")
        logger.info(result.get("video_instructions", "NO INSTRUCTIONS"))
        logger.info("==== OpenAI Video Instructions END ====")

        return result
    
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return None

def summarize_image_batch(client, images, prompt, batch_idx):
    """
    images: List[PIL.Image]
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert AI tutor. "
                "Summarize the following PDF pages clearly and concisely. "
                "Focus on formulas, definitions, and key explanations."
            ),
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"[Batch {batch_idx}] {prompt}"},
                *[
                    {
                        "type": "image_url",
                        "image_url": {"url": img},
                    }
                    for img in images
                ],
            ],
        },
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2,
    )

    return completion.choices[0].message.content

@shared_task(name="studio.analyze_pdf_vision")
def analyze_pdf_vision(job_id: int, file_path: str, prompt: str):
    """
    1) PDF → base64 이미지 리스트
    2) Vision batch(gpt-4o-mini)로 "텍스트만" 부분 요약 생성 (JSON/비디오 지시 X)
    3) 부분 요약들을 텍스트 모델(gpt-4o)로 합쳐 최종 {summary, video_instructions} JSON 생성
    4) video_instructions 기반 영상 렌더
    5) S3 업로드
    6) Spring 콜백
    """
    task_start = time.time()
    logger.info("===== analyze_pdf_vision started job_id=%s file=%s =====", job_id, file_path)

    base64_images = None
    callback_body = None

    # -----------------------------
    # config (여기만 조절하면 됨)
    # -----------------------------
    VISION_MODEL = "gpt-4o-mini"   # ✅ 배치 비전은 mini로
    FINAL_MODEL = "gpt-4o"         # ✅ 최종 합치기/비디오 지시는 여기서만
    VISION_BATCH_SIZE = 5          # ✅ 안전빵(5도 가능하지만 터지면 3으로)
    VISION_MAX_TOKENS = 500        # ✅ 부분요약 길이 제한(토큰 폭주 방지)
    FINAL_MAX_TOKENS = 2200        # ✅ 최종 JSON 길이 제한
    BETWEEN_BATCH_SLEEP_SEC = 0.2  # ✅ 짧은 텀(너무 빠르면 RPM도 터짐)

    def chunked(lst, size):
        for i in range(0, len(lst), size):
            yield lst[i:i + size]

    def to_data_url(img_base64: str) -> str:
        # base64 문자열(순수 base64) → data url
        if img_base64.startswith("data:image/"):
            return img_base64
        return f"data:image/png;base64,{img_base64}"

    def summarize_vision_batch(image_batch_base64: list[str], user_request: str, batch_idx: int) -> str:
        """
        ✅ 배치 단계: '텍스트만' 뽑기 (JSON X, video_instructions X)
        """
        content = [{"type": "text", "text": (
            f"[Batch {batch_idx}] 아래 페이지들만 보고, 수식/정의/핵심 개념을 정보밀도 높게 요약해.\n"
            f"- 전체 문서 요약 금지\n"
            f"- 중요한 수식은 가능하면 그대로 적기\n"
            f"- 불릿으로 써도 됨\n"
            f"사용자 요청(참고): {user_request}"
        )}]

        for b64 in image_batch_base64:
            content.append({
                "type": "image_url",
                "image_url": {"url": to_data_url(b64)},
            })

        resp = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert AI tutor. Extract formulas, definitions, and key explanations from these pages only."},
                {"role": "user", "content": content},
            ],
            temperature=0.2,
            max_tokens=VISION_MAX_TOKENS,
        )
        return (resp.choices[0].message.content or "").strip()

    def generate_final_json(partial_summaries: list[str], user_request: str) -> dict:
        """
        ✅ 최종 단계: 텍스트만으로 {summary, video_instructions} JSON 만들기
        """
        # 부분요약이 너무 길면 TPM/RPM 다 터짐 → 합치기 전에 살짝 다이어트
        # (너무 aggressive 하면 정보 손실이라, 여기선 "상한"만 걸자)
        trimmed = []
        for s in partial_summaries:
            s = (s or "").strip()
            if len(s) > 6000:
                s = s[:6000] + " ..."
            trimmed.append(s)

        final_prompt = f"""
You are given partial summaries extracted from different parts of a PDF.

User request:
{user_request}

Task:
1) Merge all partial summaries into ONE coherent global summary.
   - MUST be one continuous flowing text
   - MUST include a concrete example starting with EXACTLY: "For an example"
   - No line breaks in the summary (replace newlines with spaces)
2) Generate detailed video_instructions for animation rendering.
   - Respect any user numerical constraints EXACTLY as written (stride/padding/kernel_size/etc.)
   - If ambiguous, mention ambiguity in video_instructions.

Partial summaries (ordered):
{chr(10).join([f"- {t}" for t in trimmed])}

Return JSON ONLY with keys: summary, video_instructions
"""

        resp = client.chat.completions.create(
            model=FINAL_MODEL,
            messages=[
                {"role": "system", "content": "You output STRICT JSON with keys: summary, video_instructions."},
                {"role": "user", "content": final_prompt},
            ],
            temperature=0.3,
            max_tokens=FINAL_MAX_TOKENS,
            response_format={"type": "json_object"},
        )

        result = json.loads(resp.choices[0].message.content.strip())

        # summary/video_instructions 개행 제거(기존 니 요구 유지)
        if "summary" in result and isinstance(result["summary"], str):
            result["summary"] = result["summary"].replace("\n", " ").strip()
        if "video_instructions" in result and isinstance(result["video_instructions"], str):
            result["video_instructions"] = result["video_instructions"].replace("\n", " ").strip()

        return result

    try:
        # -------------------------------------------------
        # 1) PDF → base64 images
        # -------------------------------------------------
        base64_images = pdf_to_base64_images(file_path)
        if not base64_images:
            raise RuntimeError("Failed to convert PDF to images")

        logger.info("PDF converted: %d pages", len(base64_images))

        # -------------------------------------------------
        # 2) Vision batch 요약 (gpt-4o-mini, 텍스트만)
        # -------------------------------------------------
        partial_summaries: list[str] = []
        for batch_idx, image_batch in enumerate(chunked(base64_images, VISION_BATCH_SIZE), start=1):
            logger.info("🧩 Vision batch %d (%d pages)", batch_idx, len(image_batch))

            part_text = summarize_vision_batch(
                image_batch_base64=image_batch,
                user_request=prompt,
                batch_idx=batch_idx,
            )

            if not part_text:
                raise RuntimeError(f"Vision batch {batch_idx} produced empty summary")

            partial_summaries.append(part_text)

            if BETWEEN_BATCH_SLEEP_SEC > 0:
                time.sleep(BETWEEN_BATCH_SLEEP_SEC)

        logger.info("Vision batches completed: %d partial summaries", len(partial_summaries))

        # -------------------------------------------------
        # 3) 부분요약 → 최종 JSON(summary + video_instructions)
        # -------------------------------------------------
        final_result = generate_final_json(partial_summaries, prompt)

        if not final_result.get("summary") or not final_result.get("video_instructions"):
            raise RuntimeError(f"Invalid final JSON result: {final_result}")

        summary_text = final_result["summary"]
        video_instructions = final_result["video_instructions"]

        logger.info("==== Final Summary BEGIN ====")
        logger.info(summary_text)
        logger.info("==== Final Summary END ====")

        logger.info("==== Video Instructions BEGIN ====")
        logger.info(video_instructions)
        logger.info("==== Video Instructions END ====")

        # -------------------------------------------------
        # 4) 영상 렌더
        # -------------------------------------------------
        video_local_path = render_video_from_instructions(video_instructions)
        logger.info("🎬 video rendered at %s", video_local_path)

        # -------------------------------------------------
        # 5) S3 업로드
        # -------------------------------------------------
        video_url = upload_to_s3(video_local_path)
        logger.info("📤 uploaded to S3: %s", video_url)

        callback_body = {
            "status": "SUCCESS",
            "summary": summary_text,
            "resultUrl": video_url,
            "errorMessage": None,
        }

    except Exception as e:
        logger.exception("[TASK] failed job_id=%s", job_id)
        callback_body = {
            "status": "FAILED",
            "summary": None,
            "resultUrl": None,
            "errorMessage": str(e),
        }

    finally:
        elapsed = time.time() - task_start
        page_count = len(base64_images) if base64_images else -1
        logger.info("[TASK END] job_id=%s elapsed=%.2fs pages=%d", job_id, elapsed, page_count)

    # -------------------------------------------------
    # 6) Spring callback (single exit)
    # -------------------------------------------------
    callback_url = f"{SPRING_CALLBACK_BASE}/api/v1/analysis/{job_id}/complete"
    logger.info("[CALLBACK] POST %s body=%s", callback_url, callback_body)

    try:
        resp = requests.post(callback_url, json=callback_body, timeout=10)
        logger.info("[CALLBACK] status=%s", resp.status_code)
    except Exception:
        logger.exception("[CALLBACK] failed job_id=%s", job_id)


# ---------------------------------------------------------------------------
# animate_algorithm — direct algorithm-name → video pipeline (no PDF required)
# ---------------------------------------------------------------------------

def _s3_key_for_slug(slug: str) -> str:
    """Deterministic S3 key: animations/SHA256(slug).mp4"""
    digest = hashlib.sha256(slug.encode()).hexdigest()
    return f"animations/{digest}.mp4"


def _s3_object_exists(key: str) -> bool:
    s3 = boto3.client("s3", region_name=S3_REGION)
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=key)
        return True
    except s3.exceptions.ClientError:
        return False
    except Exception:
        return False


def _upload_to_s3_with_key(file_path: str, key: str) -> str:
    s3 = boto3.client("s3", region_name=S3_REGION)
    s3.upload_file(
        file_path,
        S3_BUCKET,
        key,
        ExtraArgs={"ContentType": "video/mp4"},
    )
    return f"https://{S3_BUCKET}.s3.amazonaws.com/{key}"


@shared_task(name="studio.animate_algorithm")
def animate_algorithm(job_id: int, algorithm: str):
    """Generate a Manim animation for a named algorithm.

    Flow:
        normalize_slug → domain classify (LLM, 5s timeout) → ExampleLibrary
        → few-shot codegen (gpt-4.1-mini) → run_manim_code → S3 (hash key)
        → Spring callback

    Error handling:
        - openai.RateLimitError      : exponential backoff, max 3 retries
        - subprocess.TimeoutExpired  : caught inside run_manim_code (fallback)
        - requests.ConnectionError   : push job_id to Redis dead-letter key
        - json.JSONDecodeError       : log + fall back to all examples
    """
    import openai
    from django.core.cache import cache  # Django Redis cache backend
    from studio.ai.example_library import normalize_slug, get_library
    from studio.ai.llm_domain import call_llm_detect_domain
    from studio.ai.patterns import DOMAIN_TO_PATTERN, PatternType
    from studio.ai.llm_codegen import call_llm_codegen_for_algorithm

    task_start = time.time()
    logger.info("animate_algorithm started job_id=%s algorithm=%r", job_id, algorithm)

    slug = normalize_slug(algorithm)
    s3_key = _s3_key_for_slug(slug)
    callback_body: dict = {}

    try:
        # 1) Cache check — return immediately if video already exists
        if _s3_object_exists(s3_key):
            video_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}"
            logger.info("animate_algorithm cache HIT slug=%s", slug)
            callback_body = {
                "status": "SUCCESS",
                "resultUrl": video_url,
                "cache": "HIT",
                "errorMessage": None,
            }
        else:
            # 2) Domain classify → PatternType (5s timeout; fallback to all examples)
            domain = None
            pattern_type = None
            try:
                domain = call_llm_detect_domain(slug.replace("_", " "))
                pattern_type = DOMAIN_TO_PATTERN.get(domain)
            except Exception as exc:
                logger.warning("animate_algorithm domain classify failed (%s) — using all examples", exc)

            # 3) Retrieve few-shot examples
            library = get_library()
            examples = library.get_examples(pattern_type, top_k=3)
            logger.info(
                "animate_algorithm slug=%s domain=%s pattern=%s examples=%s",
                slug, domain, pattern_type,
                [e.get("tag") for e in examples],
            )

            # 4) Codegen with exponential backoff on rate limit
            manim_code = None
            for attempt in range(1, 4):
                try:
                    manim_code = call_llm_codegen_for_algorithm(algorithm, examples)
                    break
                except openai.RateLimitError:
                    wait = 2 ** attempt  # 2s, 4s, 8s
                    logger.warning("RateLimitError, retrying in %ds (attempt %d/3)", wait, attempt)
                    time.sleep(wait)

            if manim_code is None:
                raise RuntimeError("Codegen failed after 3 rate-limit retries")

            # 5) Render
            render_start = time.perf_counter()
            output_dir = RESULT_DIR / "animations"
            output_name = f"{slug}.mp4"
            video_local_path = run_manim_code(manim_code, output_dir, output_name)
            render_time = time.perf_counter() - render_start

            # 6) Upload to S3 with deterministic hash key
            video_url = _upload_to_s3_with_key(video_local_path, s3_key)
            logger.info(
                "animate_algorithm",
                extra={
                    "algorithm": slug,
                    "domain": domain,
                    "pattern_type": str(pattern_type),
                    "examples_used": [e.get("tag") for e in examples],
                    "cache": "MISS",
                    "render_time_s": round(render_time, 2),
                    "job_id": job_id,
                },
            )

            callback_body = {
                "status": "SUCCESS",
                "resultUrl": video_url,
                "cache": "MISS",
                "errorMessage": None,
            }

    except Exception as exc:
        logger.exception("animate_algorithm failed job_id=%s", job_id)
        callback_body = {
            "status": "FAILED",
            "resultUrl": None,
            "cache": "MISS",
            "errorMessage": str(exc),
        }

    finally:
        elapsed = time.time() - task_start
        logger.info("animate_algorithm done job_id=%s elapsed=%.2fs", job_id, elapsed)

    # 7) Spring callback
    callback_url = f"{SPRING_CALLBACK_BASE}/api/v1/analysis/{job_id}/complete"
    try:
        resp = requests.post(callback_url, json=callback_body, timeout=10)
        logger.info("[ANIMATE_CALLBACK] status=%s job_id=%s", resp.status_code, job_id)
    except requests.ConnectionError:
        dead_letter_key = f"gifpt:callback:dead:{job_id}"
        try:
            cache.set(dead_letter_key, json.dumps(callback_body), timeout=None)
            logger.error(
                "[ANIMATE_CALLBACK] Spring unreachable — pushed to dead-letter key=%s", dead_letter_key
            )
        except Exception:
            logger.exception("[ANIMATE_CALLBACK] failed to write dead-letter job_id=%s", job_id)
    except Exception:
        logger.exception("[ANIMATE_CALLBACK] unexpected error job_id=%s", job_id)
