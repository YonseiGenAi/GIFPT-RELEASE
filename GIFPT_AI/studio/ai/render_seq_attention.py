# ai/render_seq_attention.py
from __future__ import annotations
import json
import tempfile
import subprocess
from pathlib import Path

MEDIA_DIR = Path("media/videos/SeqAttentionScene")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent  

def render_seq_attention(attn_ir: dict, out_basename: str = "attn_demo", fmt: str = "mp4") -> str:
    """
    attn_ir 예시:
    {
      "pattern_type": "seq_attention",
      "raw_text": "I want to eat",

      "tokens": ["I", "want", "to", "eat"],
      "weights": [...],
      "query_index": 3,

      "next_token": {                           
      "candidates": ["pizza", "something", "now", "more"],
      "probs": [0.55, 0.20, 0.15, 0.10]
      }
    }
    """

    scene_template = r"""
from manim import *
import json, sys

# === sys.path에 프로젝트 루트 추가해서 'app' 패키지가 보이게 만들기 ===
PROJECT_ROOT = r"__PROJECT_ROOT__"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from ai.layout_utils import (
    create_circle_node,
    layout_row,
    autorescale_group,
    LayoutMixin,
)

class SeqAttentionScene(Scene, LayoutMixin):
    def construct(self):
        data = json.loads(r'''__ATTN_JSON__''')

        tokens = data["tokens"]
        weights = data["weights"]
        q_idx = int(data.get("query_index", 0))


        raw_text = data.get("raw_text")
        if raw_text is None:
            raw_text = " ".join(tokens)

        # === 1. 문장 / 토큰 시각화 ===
        sentence_text = raw_text
        sentence = Text(sentence_text, font_size=28, color=GRAY_B)
        sentence.to_edge(UP, buff=0.5)

        token_nodes = [create_circle_node(t, radius=0.45) for t in tokens]
        nodes_group = layout_row(token_nodes, center=UP * 0.5)
        autorescale_group(nodes_group)

        title = Text("Transformer Self-Attention (Single Head)", font_size=30, color=YELLOW_B)
        title.to_edge(UP, buff=0.1)

        self.play(Write(title))
        self.play(FadeIn(sentence, shift=DOWN * 0.2))
        self.play(FadeIn(nodes_group, lag_ratio=0.1))
        self.wait(0.3)

        # === 2. query 토큰 강조 ===
        query_node = token_nodes[q_idx]
        q_circle, q_label = query_node

        query_highlight = Circle(
            radius=q_circle.radius * 1.45,
            color=YELLOW,
            stroke_width=4,
        ).move_to(query_node.get_center())

        query_label = Text(f"query: '{tokens[q_idx]}'", font_size=26, color=YELLOW_B)
        query_label.next_to(nodes_group, UP, buff=0.4)

        self.play(Create(query_highlight), Write(query_label))
        self.wait(0.3)

        # === 3. attention weight (query -> others) 선으로 표현 ===
        if isinstance(weights[0], list):
            row = weights[q_idx]
        else:
            row = weights

        max_w = max(row) if row else 1.0
        if max_w <= 0:
            max_w = 1.0

        edges = []
        for tgt_node, w in zip(token_nodes, row):
            t_circle, _ = tgt_node
            line = Line(
                query_node.get_bottom(),
                tgt_node.get_top(),
                stroke_color=BLUE_B,
                stroke_width=2 + 6 * (w / max_w),
                stroke_opacity=0.25 + 0.75 * (w / max_w),
                buff=0.1,
            )
            edges.append(line)

        edge_group = VGroup(*edges)
        self.play(Create(edge_group), run_time=0.8)
        self.wait(0.4)

        # === 4. 각 토큰 아래에 attention bar 시각화 ===
        bars = []
        bar_labels = []
        for tgt_node, w in zip(token_nodes, row):
            h = 0.35 + 1.2 * (w / max_w)
            bar = Rectangle(
                width=0.18,
                height=h,
                fill_color=BLUE,
                fill_opacity=0.65,
                stroke_color=WHITE,
                stroke_width=1,
            )
            bar.next_to(tgt_node, DOWN, buff=0.4)
            bars.append(bar)

            txt = MathTex(f"{w:.2f}").scale(0.45).set_color(WHITE)
            txt.next_to(bar, DOWN, buff=0.1)
            bar_labels.append(txt)

        bar_group = VGroup(*bars)
        label_group = VGroup(*bar_labels)

        self.play(FadeIn(bar_group, shift=DOWN * 0.2), run_time=0.8)
        self.play(FadeIn(label_group), run_time=0.4)

        legend = Text("higher weight \u2192 thicker & more opaque", font_size=22, color=GRAY_B)
        legend.to_edge(DOWN, buff=0.4)
        self.play(FadeIn(legend))
        self.wait(0.6)

        # === 5. context 벡터 노드 (attention 결과 요약) ===
        context_node = create_circle_node("context", radius=0.5)
        context_group = VGroup(context_node)
        context_group.next_to(query_node, RIGHT, buff=2.0)

        ctx_label = Text("weighted\nsum of values", font_size=20, color=GRAY_B)
        ctx_label.next_to(context_group, UP, buff=0.2)

        # query에서 context로 흐름 강조
        arrow_q_ctx = Arrow(
            query_node.get_right(),
            context_group.get_left(),
            buff=0.1,
            stroke_color=BLUE_B,
            stroke_width=3,
        )

        self.play(FadeIn(context_group), FadeIn(ctx_label), Create(arrow_q_ctx), run_time=0.8)
        self.wait(0.4)

        # === 6. Next-token 분포 (softmax over vocabulary) ===

        # 설명용 확률 분포 (실제 값이 아니라 직관용)
        nt = data.get("next_token", {}) 

        vocab_tokens = nt.get("candidates", ["pizza", "salad", "sleep", "movie"])
        probs = nt.get("probs", [0.50, 0.20, 0.15, 0.15])

        # 길이 안 맞으면 뒷부분 잘라서 최소한 씬이 안 깨지게
        if len(probs) != len(vocab_tokens):
            m = min(len(probs), len(vocab_tokens))
            vocab_tokens = vocab_tokens[:m]
            probs = probs[:m]

        vocab_nodes = [create_circle_node(t, radius=0.4) for t in vocab_tokens]
        vocab_group = VGroup(*vocab_nodes).arrange(DOWN, buff=0.4)
        vocab_group.to_edge(RIGHT, buff=1.0)
        vocab_group.shift(UP * 0.3)

        vocab_title = Text("candidate next tokens", font_size=22, color=GRAY_B)
        vocab_title.next_to(vocab_group, UP, buff=0.3)

        arrow_ctx_vocab = Arrow(
            context_group.get_right(),
            vocab_group.get_left(),
            buff=0.1,
            stroke_color=BLUE_B,
            stroke_width=3,
        )

        self.play(
            Create(arrow_ctx_vocab),
            FadeIn(vocab_group, lag_ratio=0.1),
            FadeIn(vocab_title),
            run_time=0.8,
        )

        # 각 vocab 옆에 확률 bar + 숫자
        prob_bars = []
        prob_labels = []
        for node, p in zip(vocab_nodes, probs):
            h = 0.35 + 1.4 * p
            bar = Rectangle(
                width=0.16,
                height=h,
                fill_color=BLUE,
                fill_opacity=0.7,
                stroke_color=WHITE,
                stroke_width=1,
            )
            bar.next_to(node, RIGHT, buff=0.3)
            prob_bars.append(bar)

            txt = MathTex(f"{p:.2f}").scale(0.4).set_color(WHITE)
            txt.next_to(bar, RIGHT, buff=0.1)
            prob_labels.append(txt)

        prob_bar_group = VGroup(*prob_bars)
        prob_label_group = VGroup(*prob_labels)

        self.play(
            FadeIn(prob_bar_group, shift=RIGHT * 0.2),
            FadeIn(prob_label_group),
            run_time=0.8,
        )
        self.wait(0.6)

        # === 7. 최고 확률 토큰 강조 + "Predicted next token" ===
        max_idx = max(range(len(probs)), key=lambda i: probs[i])
        best_node = vocab_nodes[max_idx]
        best_bar = prob_bars[max_idx]

        self.play(
            best_bar.animate.set_fill(color=YELLOW, opacity=0.9).scale(1.05),
            run_time=0.6,
        )

        pred_label = Text(
            f"Predicted next token: '{vocab_tokens[max_idx]}'",
            font_size=26,
            color=YELLOW_B,
        )
        pred_label.next_to(prob_bar_group, DOWN, buff=0.5)
        self.play(Write(pred_label))
        self.wait(0.6)

        # === 8. 시퀀스에 예측 토큰을 실제로 붙이는 컷 ===
        # vocab 토큰 하나를 복사해서 기존 시퀀스 오른쪽에 붙이기
        new_token = best_node.copy()
        new_token.next_to(nodes_group, RIGHT, buff=0.8)

        self.play(TransformFromCopy(best_node, new_token), run_time=0.8)

        full_sentence = Text(
            sentence_text + "  " + vocab_tokens[max_idx],
            font_size=28,
            color=WHITE,
        )
        full_sentence.to_edge(DOWN, buff=1.0)

        self.play(Write(full_sentence), run_time=0.8)
        self.wait(1.2)
"""


    scene_code = (
        scene_template
        .replace("__ATTN_JSON__", json.dumps(attn_ir))
        .replace("__PROJECT_ROOT__", str(PROJECT_ROOT))
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp.write(scene_code)
        tmp_path = tmp.name

    cmd = [
        "manim",
        "-ql",
        tmp_path,
        "SeqAttentionScene",
        "--format",
        fmt,
        "-o",
        f"{out_basename}.{fmt}",
    ]
    subprocess.run(cmd, check=True)

    video_path = MEDIA_DIR / f"{out_basename}.{fmt}"
    return str(video_path)
