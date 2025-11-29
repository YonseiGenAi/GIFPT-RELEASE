# GIFPT_AI/studio/tasks_vision.py

import os
import logging
import requests
import base64
import json
from io import BytesIO
import shutil
import time
from typing import Optional

from celery import shared_task
from django.conf import settings

from openai import OpenAI
import fitz  # PyMuPDF
from PIL import Image

logger = logging.getLogger(__name__)

SPRING_CALLBACK_BASE = os.environ.get("SPRING_CALLBACK_BASE", "http://spring:8080")
UPLOAD_DIR = os.environ.get("GIFPT_UPLOAD_DIR", "/data/uploads")
RESULT_DIR = os.environ.get("GIFPT_RESULT_DIR", "/data/results")

DEMO_API_KEY = os.environ.get("DEMO_API_KEY")  # optional

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _extract_video_path_from_demo(resp_json: dict) -> Optional[str]:
    """Try common keys to get video path from demo /generate response."""
    if not isinstance(resp_json, dict):
        return None
    return (
        resp_json.get("video_path")
        or resp_json.get("output")
        or resp_json.get("output_path")
        or (resp_json.get("media") or {}).get("video")
    )


def call_demo_generate(user_text: str, timeout: int = 300) -> dict:
    """
    Call demo service /generate with given text and return JSON.
    Raises on non-2xx.
    """
    url = f"{SPRING_CALLBACK_BASE}/generate"
    headers = {"Content-Type": "application/json"}
    if DEMO_API_KEY:
        headers["Authorization"] = f"Bearer {DEMO_API_KEY}"
    payload = {"text": user_text}
    t0 = time.perf_counter()
    logger.info("Calling demo /generate: %s", url)
    r = requests.post(url, json=payload, headers=headers, timeout=timeout)
    dt = time.perf_counter() - t0
    logger.info("demo /generate status=%s time=%.2fs", r.status_code, dt)
    r.raise_for_status()
    return r.json()


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


@shared_task(name="studio.analyze_pdf_vision")
def analyze_pdf_vision(job_id: int, file_path: str, prompt: str):
    """
    Celery task: Analyze PDF using vision model.
    - jobId, pdf path, user prompt
    - Convert PDF to images
    - Generate summary + video instructions using OpenAI vision
    - Call demo /generate to render video
    - Spring callback with results
    """
    logger.info("analyze_pdf_vision started job_id=%s input_path=%s", job_id, file_path)

    # Handle relative vs absolute paths
    if not os.path.isabs(file_path):
        # 🔥 avoid duplicated 'uploads/' prefix
        cleaned = file_path.replace("uploads/", "", 1)
        pdf_path = os.path.join(UPLOAD_DIR, cleaned)
    else:
        pdf_path = file_path

    try:
        # 1) Convert PDF to base64 images
        base64_images = pdf_to_base64_images(pdf_path)
        
        if not base64_images:
            raise Exception("Failed to convert PDF to images")

        # 2) Generate AI summary with vision model
        result = generate_summary_from_images(base64_images, prompt)
        
        if not result:
            raise Exception("Failed to generate summary from images")

        # Combine summary and video instructions into continuous text
        continuous_text = (result.get('summary', '') + ' ' + result.get('video_instructions', '')).strip()

        # 3) Call demo pipeline to render video from text
        demo_resp = call_demo_generate(continuous_text)
        logger.info("demo response keys: %s", list(demo_resp.keys()))
        video_src = _extract_video_path_from_demo(demo_resp)
        if not video_src:
            raise Exception("demo returned no video_path")
        if not os.path.exists(video_src):
            # If demo runs in another container, consider a shared volume or URL fetch
            logger.warning("video path not found locally: %s", video_src)

        # 4) Copy video into RESULT_DIR (for Spring serving)
        os.makedirs(RESULT_DIR, exist_ok=True)
        result_rel = f"{job_id}_result.mp4"
        result_abs = os.path.join(RESULT_DIR, result_rel)
        try:
            shutil.copyfile(video_src, result_abs)
            logger.info("copied video to %s", result_abs)
        except Exception as copy_err:
            logger.warning("copy failed (%s), using original path", copy_err)
            result_abs = video_src
            result_rel = os.path.basename(video_src)

        result_url = result_rel

        callback_payload = {
            "status": "SUCCESS",
            "resultUrl": result_url,
            "summary": continuous_text,
            "errorMessage": None,
        }

    except Exception as e:
        logger.exception("analyze_pdf_vision failed job_id=%s", job_id)
        callback_payload = {
            "status": "FAILED",
            "resultUrl": None,
            "summary": None,
            "errorMessage": str(e),
        }

    # 5) Spring callback
    try:
        cb_url = f"{SPRING_CALLBACK_BASE}/api/v1/analysis/{job_id}/complete"
        logger.info("calling spring callback %s with %s", cb_url, callback_payload["status"])
        requests.post(cb_url, json=callback_payload, timeout=10)
    except Exception:
        logger.exception("failed to callback spring for job_id=%s", job_id)
