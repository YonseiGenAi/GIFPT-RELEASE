# app/render_sorting.py
import json, os
import subprocess
import tempfile
from pathlib import Path
from textwrap import dedent

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


def render_sorting(trace_ir: dict,
                   out_basename: str = "sorting_demo",
                   fmt: str = "mp4") -> str:
    """
    trace_ir 예시 형식:

    {
      "algorithm": "bubble_sort",
      "input": { "array": [5, 1, 4, 2] },
      "trace": [
        { "step": 1, "compare": [0,1], "swap": true,  "array": [1,5,4,2] },
        { "step": 2, "compare": [1,2], "swap": true,  "array": [1,4,5,2] },
        { "step": 3, "compare": [2,3], "swap": true,  "array": [1,4,2,5] },
        ...
      ],
      "metadata": { "domain": "sorting" }
    }
    """
    trace_json = json.dumps(trace_ir, ensure_ascii=False)

    # CNN처럼 placeholder 치환 방식 사용
    scene_template = r"""
from manim import *
import json
from app.layout_utils import (
    create_circle_node,
    layout_row,
    autorescale_group,
    LayoutMixin,
)

class SortingScene(Scene, LayoutMixin):
    def construct(self):
        trace = json.loads(r'''__TRACE_JSON__''')

        algo_name = trace.get("algorithm", "Sorting")
        arr = trace["input"]["array"]
        steps = trace.get("trace", [])

        # === 1. 제목 ===
        title = Text(f"Algorithm: {algo_name}", font_size=32, color=YELLOW_B)
        title.to_edge(UP, buff=0.4)
        self.play(Write(title))

        # === 2. 초기 배열 노드 생성 ===
        nodes = [create_circle_node(str(v), radius=0.5) for v in arr]

        nodes_group = layout_row(nodes, center=ORIGIN)
        autorescale_group(nodes_group)

        self.play(FadeIn(nodes_group, lag_ratio=0.1))
        self.wait(0.5)

        # 인덱스 라벨 (0,1,2,...) 아래에 깔기
        index_labels = []
        for idx, node in enumerate(nodes):
            idx_text = Text(str(idx), font_size=20, color=GRAY_B)
            idx_text.next_to(node, DOWN, buff=0.15)
            index_labels.append(idx_text)
        idx_group = VGroup(*index_labels)
        self.play(FadeIn(idx_group, lag_ratio=0.05))

        current_nodes = nodes  # 인덱스 접근용

        # selection sort용 “현재 최소값 후보” 마커
        min_marker = None

        # === 3. step trace에 따라 비교/스왑 애니메이션 ===
        cleaned_steps = []
        prev = None
        for s in steps:
            if "compare" not in s:
                continue
            i, j = s["compare"]
            swap_flag = bool(s.get("swap", False))
            key = (i, j, swap_flag)
            if key == prev:
                # 같은 쌍에 같은 swap 여부가 연달아 나오면 스킵
                continue
            cleaned_steps.append(s)
            prev = key

        for s in cleaned_steps:
            i, j = s["compare"]
            swap = s.get("swap", False)

            # selection sort면 min_index 활용
            min_idx = s.get("min_index", None)
            if algo_name == "selection_sort" and min_idx is not None:
                if 0 <= min_idx < len(current_nodes):
                    target_node = current_nodes[min_idx]
                    circ = target_node[0]  # VGroup(circle, text) 중 circle

                    new_marker = Circle(
                        radius=circ.radius * 1.3,
                        color=BLUE_B,
                        stroke_width=4,
                    ).move_to(target_node.get_center())

                    if min_marker is None:
                        self.play(Create(new_marker), run_time=0.15)
                    else:
                        self.play(Transform(min_marker, new_marker), run_time=0.15)
                    min_marker = new_marker

            # 안전 guard (LLM이 이상한 인덱스 내보내면 무시)
            if not (0 <= i < len(current_nodes) and 0 <= j < len(current_nodes)):
                continue

            ni = current_nodes[i]
            nj = current_nodes[j]

            circ_i = ni[0]  # circle
            circ_j = nj[0]  

            # 비교 하이라이트
            hi_i = Circle(
                radius=circ_i.radius * 1.15,
                color=YELLOW,
                stroke_width=3,
            ).move_to(ni.get_center())

            hi_j = Circle(
                radius=circ_j.radius * 1.15,
                color=YELLOW,
                stroke_width=3,
            ).move_to(nj.get_center())

            self.play(Create(hi_i), Create(hi_j), run_time=0.3)

            if swap:
                circle_i, text_i = ni
                circle_j, text_j = nj

                orig_fill_i = circle_i.get_fill_color()
                orig_opacity_i = circle_i.get_fill_opacity()
                orig_stroke_i = circle_i.get_stroke_color()
                orig_width_i = circle_i.get_stroke_width()

                orig_fill_j = circle_j.get_fill_color()
                orig_opacity_j = circle_j.get_fill_opacity()
                orig_stroke_j = circle_j.get_stroke_color()
                orig_width_j = circle_j.get_stroke_width()

                # 1) 원 전체를 빨갛게 (fill + stroke)
                self.play(
                    circle_i.animate.set_fill(color=RED, opacity=0.6).set_stroke(color=RED, width=3),
                    circle_j.animate.set_fill(color=RED, opacity=0.6).set_stroke(color=RED, width=3),
                    run_time=0.2,
                )

                # 2) swap 이동
                pos_i = ni.get_center()
                pos_j = nj.get_center()
                self.play(
                    ni.animate.move_to(pos_j),
                    nj.animate.move_to(pos_i),
                    run_time=0.6,
                )

                # 3) 색 되돌리기 (기본값: 흰색 fill, 흰색 stroke)
                self.play(
                    circle_i.animate
                        .set_fill(orig_fill_i, opacity=orig_opacity_i)
                        .set_stroke(color=orig_stroke_i, width=orig_width_i),
                    circle_j.animate
                        .set_fill(orig_fill_j, opacity=orig_opacity_j)
                        .set_stroke(color=orig_stroke_j, width=orig_width_j),
                    run_time=0.2,
                )


                # 리스트 상에서도 교환
                current_nodes[i], current_nodes[j] = current_nodes[j], current_nodes[i]


            # 하이라이트 제거
            self.play(FadeOut(hi_i), FadeOut(hi_j), run_time=0.2)

        # 마지막에 min 마커 제거
        if min_marker is not None:
            self.play(FadeOut(min_marker), run_time=0.3)

        # === 4. 정렬 완료 강조 ===
        # 마지막 배열을 초록색 테두리로 바꿔서 "완료" 느낌
        for node in current_nodes:
            box, txt = node
            box.set_stroke(color=GREEN_B)
        self.play(*[Indicate(node, color=GREEN) for node in current_nodes], run_time=0.8)

        done_label = Text("Sorted!", font_size=28, color=GREEN_B)
        done_label.next_to(nodes_group, DOWN, buff=0.8)
        self.play(Write(done_label))
        self.wait(1.5)
"""

    scene_code = scene_template.replace("__TRACE_JSON__", trace_json)

    # 임시 파이썬 파일로 저장
    tmpdir = tempfile.mkdtemp()
    py_path = Path(tmpdir) / "sorting_scene.py"
    py_path.write_text(scene_code, encoding="utf-8")

    # 출력 디렉토리
    out_dir = Path("media") / "sorting"
    out_dir.mkdir(parents=True, exist_ok=True)

    # manim 실행 =
    cmd = [
        "manim",
        str(py_path),
        "SortingScene",
        "-ql",  
        "-o",
        f"{out_basename}.mp4",
    ]

    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.run(cmd, check=True, env=env)
    
    video_dir = os.path.join(PROJECT_ROOT, "media", "videos")
    return os.path.join(video_dir, "sorting_scene", "480p15", f"{out_basename}.mp4")

