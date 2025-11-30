# ai/prompts.py

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
      "seed": 1
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

User text:
{text}
"""
    },

      "sorting_trace": {
      "system": """
  You are a sorting algorithm visual trace generator.

  Your job:
  1. Identify which sorting algorithm the user wants (bubble_sort, selection_sort, insertion_sort, quicksort, merge_sort, etc.).
  2. Extract the array from the user request.
  3. Generate the FULL step-by-step trace for that sorting algorithm.

  Return ONLY JSON.
  """,
      "template": """
  User request:
  {text}

  Extract:
  - the sorting algorithm name (bubble_sort / selection_sort / insertion_sort / quicksort / merge_sort / heap_sort ...)
  - the integer array

  Then output JSON like:

  {{
    "algorithm": "<detected_sorting_algorithm>",
    "input": { "array": [...] },
    "trace": [
      { "step": 1, "compare": [i, j], "swap": true/false, "array": [...] },
      ...
    ]
  }}

  Rules:
  - "algorithm" must match the sorting algorithm truly intended or implied by the user request.
  - If the user clearly mentions the algorithm name, obey it.
  - If the user does NOT mention any algorithm, choose the algorithm that best fits the description.
  - "array" must come from the user request.
  - "trace" must be a fully detailed chronological step list for THAT algorithm.
  - Do NOT output anything except valid JSON.
  """
  },



    "seq_attention": {
        "system": "You are a precise JSON generator for transformer self-attention & next-token visualization. Output ONLY JSON.",
        "template": """
You are given a USER REQUEST that may include:
- An example input sentence (often in English) that should be fed into a transformer.
- Surrounding Korean explanation such as "라는 문장의 next token prediction이 어떻게 동작해?" and other context.

From this USER REQUEST, do the following:

1. Extract the short **input sequence** that will be fed into the transformer.
   - Prefer the English part that looks like an example sentence, e.g. "I want to play".
   - If the user writes something like `I want to play라는 문장의 next token prediction이...`,
     then the input sequence MUST be exactly "I want to play".
   - If there are quotes, backticks, or text before '라는 문장', treat that as the candidate.
   - If multiple candidates exist, choose the simplest short phrase (3–10 tokens) that looks like a natural input.
   - If you truly cannot find any clear example, fall back to using the entire request text as raw_text.

2. Use ONLY that extracted input sequence as "raw_text" and "tokens".
   - Do NOT include the surrounding Korean question or explanation in "raw_text".
   - "tokens" must be a whitespace-based tokenization of raw_text.

Then produce a JSON object with the following structure:

{{
  "pattern_type": "seq_attention",
  "raw_text": "<the extracted input sequence>",
  "tokens": ["...", "...", "..."],
  "weights": [w_0, w_1, ...],
  "query_index": <integer index of the token that acts as the query>,
  "next_token": {{
    "candidates": ["...", "...", "..."],
    "probs": [p_0, p_1, p_2]
  }}
}}

Rules:
- "raw_text" MUST be exactly the extracted input sequence (e.g. "I want to play"), NOT the whole user request.
- "tokens" MUST be a tokenization of that raw_text, in order.
- "weights" MUST be a list of floats, one per token, that highlight which tokens are most attended to by the query token.
- "query_index" MUST be a valid index into the tokens array.
- "next_token.candidates" MUST be likely next tokens in English.
- "next_token.probs" MUST be a list of floats (0–1) that sum to 1.

USER REQUEST:
{text}
"""
    },

}


