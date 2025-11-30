import os
import json
import tempfile
import subprocess
from pathlib import Path

# --- 출력 경로 기본 설정 ---
MEDIA_DIR = Path("media/videos/IRScene")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


# --- 1️⃣ trace 자동 확장 함수 ---
def expand_bubble_trace(ir: dict) -> dict:
    """LLM이 불완전한 trace를 생성하더라도 버블 정렬 전체 과정을 자동 생성"""
    components = ir.get("components", [])
    arr = [int(c["label"]) for c in components]
    events = []
    step = 1

    for i in range(len(arr)):
        for j in range(len(arr) - i - 1):
            events.append({
                "op": "compare",
                "from": f"arr{j}",
                "to": f"arr{j+1}",
                "step": step
            })
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
                events.append({
                    "op": "swap",
                    "from": f"arr{j}",
                    "to": f"arr{j+1}",
                    "step": step
                })
        step += 1

    ir["events"] = events
    return ir


# --- 2️⃣ render 함수 ---
def render_manim_scene(ir: dict, out_basename: str = "result", fmt: str = "gif") -> str:
    """
    IR(JSON)을 기반으로 버블 정렬 과정을 시각화하는 Manim Scene 생성 및 렌더링
    """
    # LLM이 준 trace를 보완
    ir = expand_bubble_trace(ir)
    ir_json_str = json.dumps(ir, ensure_ascii=False, indent=2)

    # --- Manim Scene 코드 ---
    scene_code = f"""
from manim import *
import json

class IRScene(Scene):
    def construct(self):
        print("🎬 IR loaded, starting bubble sort animation...")
        IR = json.loads(r'''{ir_json_str}''')

        # --- Step 1: 초기 원 배열 그리기 ---
        circles = []
        x_start = -3
        for i, comp in enumerate(IR.get("components", [])):
            value = str(comp.get("label", "?"))
            c = Circle(radius=0.5, color=YELLOW, fill_opacity=0.6).shift(RIGHT * (x_start + i * 1.4))
            label = Text(value, font_size=36, color=BLACK).move_to(c.get_center())
            group = VGroup(c, label)
            self.add(group)
            circles.append(group)

        self.wait(0.8)

        # --- Step 2: 이벤트 재생 (compare + swap) ---
        current_step = 1
        for e in IR.get("events", []):
            op = e.get("op")
            i = int(e["from"].replace("arr", ""))
            j = int(e["to"].replace("arr", ""))

            if op == "compare":
                # 비교 시 살짝 들썩
                self.play(
                    circles[i].animate.shift(UP*0.25),
                    circles[j].animate.shift(UP*0.25),
                    run_time=0.2
                )
                self.play(
                    circles[i].animate.shift(DOWN*0.25),
                    circles[j].animate.shift(DOWN*0.25),
                    run_time=0.2
                )

            elif op == "swap":
                # swap 시 실제 위치 교환 + 색 변화
                pos_i = circles[i].get_center()
                pos_j = circles[j].get_center()
                self.play(
                    circles[i][0].animate.set_color(ORANGE),
                    circles[j][0].animate.set_color(ORANGE),
                    run_time=0.2
                )
                self.play(
                    circles[i].animate.move_to(pos_j),
                    circles[j].animate.move_to(pos_i),
                    run_time=0.6
                )
                circles[i], circles[j] = circles[j], circles[i]
                self.play(
                    circles[i][0].animate.set_color(YELLOW),
                    circles[j][0].animate.set_color(YELLOW),
                    run_time=0.2
                )

            # 패스 간 잠시 멈춤
            step_num = e.get("step", 0)
            if step_num > current_step:
                self.wait(0.3)
                current_step = step_num

        # --- Step 3: 정렬 완료 표시 ---
        self.wait(0.5)
        self.play(*[c[0].animate.set_color(GREEN) for c in circles], run_time=1.0)
        self.wait(1.0)
"""

    # --- 임시 Scene 파일 작성 ---
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp_file:
        tmp_file.write(scene_code)
        tmp_path = tmp_file.name

    print(f"📝 Temporary scene written to: {tmp_path}")

    # --- Manim 렌더 실행 ---
    cmd = [
        "manim",
        "-ql",
        tmp_path,
        "IRScene",
        "--format", fmt,
        "-o", f"{out_basename}.{fmt}",
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print("🔥 Manim render failed:", e)
        raise RuntimeError(f"Manim rendering failed: {e}")

    output_path = MEDIA_DIR / f"{out_basename}.{fmt}"
    print(f"✅ Render complete: {output_path.resolve()}")
    return str(output_path)

