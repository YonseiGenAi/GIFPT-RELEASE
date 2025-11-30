# app/prompts.py

DOMAIN_PROMPTS = {
    "cnn_param": {
        "system": "You are a precise JSON generator for CNN visualization IRs. Output ONLY JSON.",
        "template": """
Generate a JSON object following the exact structure below.
Do NOT include explanations, comments, or additional text.

{{
  "ir": {{
    "metadata": {{"domain": "cnn_param"}},
    "params": {{
      "input_size": <integer>,
      "kernel_size": <integer>,
      "stride": <integer>,
      "padding": <integer>,
      "seed": 3
    }}
  }},
  "basename": "cnn_forward_param",
  "out_format": "mp4"
}}


Rules:
- "NxN 행렬" or "matrix" → input_size
- "kernel size", "filter", "커널" → kernel_size
- input_size는 padding을 포함하지 않는다.
- 절대 사용자의 수치를 변경하거나 추정하지 말라.
- JSON 외의 문장은 절대 포함하지 말라.

- If any value is missing in the user's text:
  - kernel_size → default to 2
  - stride → default to 1
  - padding → default to 1
  - input_size → default to 3
- Always respond in JSON only.

User text:
{text}
"""
    }
}

