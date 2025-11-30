# app/render_cnn_matrix.py
from __future__ import annotations
import json
import tempfile
import subprocess
from pathlib import Path

MEDIA_DIR = Path("media/videos/CNNScene")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

def render_cnn_matrix(cfg: dict, out_basename="cnn_param_demo", fmt="mp4") -> str:
    """
    cfg 예시:
    {
      "input_size": 4,
      "kernel_size": 3,
      "stride": 1,
      "padding": 1,
      "seed": 7
    }
    """


    scene_template = r"""
from manim import *
import random, json

class CNNParamScene(Scene):
    def construct(self):
        cfg = json.loads(r'''__CFG_JSON__''')
        random.seed(cfg.get("seed", 7))

        input_size  = int(cfg.get("input_size", 4))
        kernel_size = int(cfg.get("kernel_size", 3))
        stride      = int(cfg.get("stride", 1))
        padding     = int(cfg.get("padding", 1))

        total = input_size + 2 * padding
        out_size = (total - kernel_size)//stride + 1

        cell, gap = 0.42, 0.02

        # (1) 입력 행렬 + 패딩
        padded_vals = [[0]*total for _ in range(total)]
        for r in range(input_size):
            for c in range(input_size):
                padded_vals[r+padding][c+padding] = random.randint(0,9)

        pad_grid = VGroup(*[
            Square(cell, color=GREY, fill_opacity=0.05)
            for _ in range(total*total)
        ]).arrange_in_grid(rows=total, cols=total, buff=gap).move_to(LEFT*3.5)
        self.add(pad_grid)

        pad_texts = []
        for r in range(total):
            row=[]
            for c in range(total):
                is_core = (padding <= r < total-padding) and (padding <= c < total-padding)
                color = WHITE if is_core else GREY
                t = Text(str(padded_vals[r][c]), font_size=24, color=color)
                t.move_to(pad_grid[r*total + c].get_center())
                row.append(t)
            pad_texts.append(row)
        self.add(*[t for row in pad_texts for t in row])

        # (2) 출력 feature map
        fmap_cells = []
        fmap_texts = [[None for _ in range(out_size)] for _ in range(out_size)]

        for i in range(out_size):
            for j in range(out_size):
                sq = Square(cell, color=BLUE, fill_opacity=0.15)
                txt = MathTex("0").scale(0.45).set_color(WHITE)
                txt.move_to(sq.get_center())
                fmap_texts[i][j] = txt
                fmap_cells.append(VGroup(sq, txt))

        fmap = VGroup(*[
            Square(cell, color=BLUE, fill_opacity=0.15)
            for _ in range(out_size*out_size)
        ]).arrange_in_grid(rows=out_size, cols=out_size, buff=gap)
        fmap.next_to(pad_grid, RIGHT, buff=2.2)
        self.add(fmap)

        # 라벨 추가
        input_label = Text("Input", color=GRAY_B, font_size=28)
        fmap_label = Text("Feature Map", color=BLUE_B, font_size=28)
        input_label.next_to(pad_grid, DOWN, buff=0.3)
        fmap_label.next_to(fmap, DOWN, buff=0.3)
        self.play(Write(input_label), Write(fmap_label))


        # (3) 커널 및 계산 함수
        kernel_vals = [[random.choice([-1,0,1]) for _ in range(kernel_size)] for _ in range(kernel_size)]

        def patch_sum(i,j):
            acc=0
            terms=[]
            for r in range(kernel_size):
                for c in range(kernel_size):
                    x = padded_vals[i*stride + r][j*stride + c]
                    w = kernel_vals[r][c]
                    acc += x*w
                    terms.append((x,w))
            return acc, terms

        # (4) 첫 번째 패치 시각화 (0,0)
        patch_cells=[pad_grid[(0+r)*total+(0+c)] for r in range(kernel_size) for c in range(kernel_size)]
        patch_box=SurroundingRectangle(VGroup(*patch_cells), color=YELLOW)
        self.play(Create(patch_box))

        kernel_grid = VGroup(*[
            Square(cell, color=YELLOW, fill_opacity=0.15)
            for _ in range(kernel_size*kernel_size)
        ]).arrange_in_grid(rows=kernel_size, cols=kernel_size, buff=gap)
        kernel_grid.next_to(patch_box, UP, buff=0.35)
        kernel_grid.align_to(patch_box, LEFT)
        kernel_grid.shift(LEFT * (cell/2 + gap/2))
        self.play(FadeIn(kernel_grid, shift=DOWN*0.2))
        
        kernel_label = Text("Kernel", color=YELLOW_B, font_size=28)
        kernel_label.next_to(kernel_grid, UP, buff=0.25)
        self.play(Write(kernel_label))


        k_texts = []
        for r in range(kernel_size):
            for c in range(kernel_size):
                kt = Text(str(kernel_vals[r][c]), font_size=24, color=YELLOW)
                kt.move_to(kernel_grid[r*kernel_size + c].get_center())
                k_texts.append(kt)
        self.add(*k_texts)

        acc00, terms00 = patch_sum(0,0)
        term_exprs = [f"{x} \\times {w}" for (x, w) in terms00]
        eq_expr = " + ".join(term_exprs) + f" = {acc00}"
        eq_line = MathTex(eq_expr).scale(0.55)
        eq_line.next_to(kernel_grid, RIGHT, buff=0.7)
        eq_line.set_color_by_tex("\\times", BLUE_A)
        eq_line.set_color_by_tex("+", WHITE)
        eq_line.set_color_by_tex("=", YELLOW)

        self.play(Write(eq_line), run_time=0.7)

        # (0,0) 결과 표시
        t00 = MathTex(str(acc00)).scale(0.5).set_color(WHITE)
        t00.move_to(fmap[0].get_center())
        fmap_texts[0][0] = t00
        self.play(FadeIn(t00))
        self.wait(0.4)

        # 커널 숫자, 글씨, 수식 제거
        self.play(FadeOut(VGroup(*k_texts)), FadeOut(eq_line), FadeOut(patch_box))
        self.play(FadeOut(kernel_label))

        # === fmap의 수치 값 저장용 리스트 ===
        fmap_vals = [[0 for _ in range(out_size)] for _ in range(out_size)]

        # (5) 이후 슬라이딩은 반투명 커널만 이동
        for i in range(out_size):
            for j in range(out_size):
                if i == 0 and j == 0:
                    continue

                # 새 패치 위치 계산
                patch_cells = [pad_grid[(i*stride+r)*total + (j*stride+c)]
                            for r in range(kernel_size) for c in range(kernel_size)]
                patch_group = VGroup(*patch_cells)
                patch_box = Rectangle(
                    width=patch_group.width + gap,
                    height=patch_group.height + gap,
                    stroke_color=YELLOW,
                    fill_color=YELLOW,
                    fill_opacity=0.18,
                    stroke_width=2
                ).move_to(patch_group)

                # 커널 이동
                self.play(ReplacementTransform(kernel_grid, patch_box), run_time=0.15)
                kernel_grid = patch_box

                # 결과 계산 및 저장
                acc, _ = patch_sum(i, j)
                fmap_vals[i][j] = acc

                txt = MathTex(str(acc)).scale(0.45).set_color(WHITE)
                txt.move_to(fmap[i*out_size + j].get_center())
                self.play(FadeIn(txt), run_time=0.05)

        self.play(FadeOut(patch_box), run_time=0.3)
        self.wait(0.3)


        # === (6) ReLU Activation 단계 ===
        relu_label = Text("ReLU Activation", color=YELLOW_B, font_size=32)
        relu_label.next_to(fmap, UP, buff=0.5)
        self.play(Write(relu_label))

        relu_vals = [[0 for _ in range(out_size)] for _ in range(out_size)]

        # 🔹 먼저 fmap 내 숫자 객체들을 따로 기록 (겹침 제거용)
        fmap_text_objects = {}
        for i in range(out_size):
            for j in range(out_size):
                # fmap 중심과 거의 일치하는 MathTex 찾기
                for mob in self.mobjects:
                    if isinstance(mob, MathTex):
                        if np.allclose(mob.get_center(), fmap[i*out_size + j].get_center(), atol=0.02):
                            fmap_text_objects[(i, j)] = mob
                            break

        # 🔹 음수인 값만 순서대로 처리
        neg_indices = [(i, j) for i in range(out_size) for j in range(out_size) if fmap_vals[i][j] < 0]

        for (i, j) in neg_indices:
            val = fmap_vals[i][j]
            neg_txt = MathTex(str(val)).scale(0.5).set_color(RED)
            zero_txt = MathTex("0").scale(0.5).set_color(GRAY)
            neg_txt.move_to(fmap[i*out_size + j].get_center())
            zero_txt.move_to(fmap[i*out_size + j].get_center())

            # 기존 텍스트 제거 후 애니메이션
            if (i, j) in fmap_text_objects:
                self.remove(fmap_text_objects[(i, j)])

            self.play(FadeIn(neg_txt, run_time=0.2))
            self.play(Transform(neg_txt, zero_txt), run_time=0.3)
            relu_vals[i][j] = 0

        # 🔹 나머지 양수는 그대로 표시 유지
        for i in range(out_size):
            for j in range(out_size):
                val = fmap_vals[i][j]
                if val >= 0:
                    relu_vals[i][j] = val

        self.wait(0.5)
        self.play(FadeOut(relu_label))




        # === (7) Max Pooling 단계 ===
        pool_size = 2
        pooled_out = out_size // pool_size
        pool_label = Text("Max Pooling", color=YELLOW_B, font_size=32)
        pool_label.next_to(fmap, UP, buff=0.5)
        self.play(Write(pool_label))

        pooled_cells = []   # 2D 구조로 셀 저장
        pooled_vals = [[0 for _ in range(pooled_out)] for _ in range(pooled_out)]

        for i in range(pooled_out):
            row_group = []
            for j in range(pooled_out):
                r0, c0 = i * pool_size, j * pool_size
                vals = [relu_vals[r0+r][c0+c] for r in range(pool_size) for c in range(pool_size)]
                max_val = max(vals)
                pooled_vals[i][j] = max_val

                patch_cells = [fmap[(r0+r)*out_size + (c0+c)] for r in range(pool_size) for c in range(pool_size)]
                pool_box = SurroundingRectangle(VGroup(*patch_cells), color=YELLOW)
                self.play(Create(pool_box), run_time=0.3)

                sq = Square(cell, color=GREEN, fill_opacity=0.15)
                txt = MathTex(str(max_val)).scale(0.5).set_color(WHITE)
                grp = VGroup(sq, txt)  # ✅ 사각형 + 숫자 묶기
                grp.move_to(fmap.get_right() + RIGHT * (2.2 + j * (cell + gap)) + DOWN * (i * (cell + gap)))

                self.play(FadeIn(grp), run_time=0.25)
                self.play(FadeOut(pool_box), run_time=0.2)

                row_group.append(grp)  # ✅ 각 행에 추가
            pooled_cells.append(row_group)  # ✅ 행 단위로 저장

        # VGroup으로 전체 풀링 맵 생성
        pooled_map = VGroup(*[grp for row in pooled_cells for grp in row])
        pooled_map.arrange_in_grid(rows=pooled_out, cols=pooled_out, buff=gap)
        pooled_map.next_to(fmap, RIGHT, buff=2.2)
        self.play(FadeIn(pooled_map))
        self.wait(0.5)
        self.play(FadeOut(pool_label))




        # === (8) Flatten 단계 ===

        # 1) Conv~Pool 블록 전체를 왼쪽으로 크게 이동해서 flatten 공간 확보
        conv_group = VGroup(
            pad_grid,
            *[t for row in pad_texts for t in row],  # 입력 숫자
            fmap,
            *[m for m in self.mobjects if isinstance(m, MathTex)],  # ✅ ReLU 이후 숫자들도 함께 이동
            pooled_map,
            input_label,
            fmap_label,
        )
        self.play(conv_group.animate.shift(LEFT * 7), run_time=1.0)

        # 2) Flatten 라벨
        flatten_label = Text("Flatten", color=PURPLE_B, font_size=32)
        flatten_label.next_to(pooled_map, UP, buff=0.4)
        self.play(Write(flatten_label))

        # 3) Flatten 칸 + 숫자 쌍으로 생성
        flat_pairs = []
        flat_values = []

        for i in range(len(pooled_vals)):
            for j in range(len(pooled_vals[0])):
                v = pooled_vals[i][j]
                flat_values.append(v)
                sq = Square(cell * 0.8, color=PURPLE, fill_opacity=0.15)
                t = MathTex(str(v)).scale(0.45).set_color(WHITE)
                t.move_to(sq.get_center())  # ✅ 숫자를 각 사각형 중심으로 이동
                pair = VGroup(sq, t)
                flat_pairs.append(pair)

        # 일렬로 나열
        flattened_group = VGroup(*flat_pairs).arrange(RIGHT, buff=0.1)
        flattened_group.next_to(pooled_map, RIGHT, buff=1.8)

        # 풀링맵 → Flatten 변환 애니메이션
        self.play(TransformFromCopy(pooled_map, flattened_group), run_time=1.2)
        self.wait(0.5)





        # === (9) Fully Connected Layer (Dense) ===
        dense_label = Text("Fully Connected Layer", color=PURPLE_B, font_size=30)
        dense_label.next_to(flattened_group, UP, buff=0.4)
        self.play(Write(dense_label))

        output_nodes = VGroup(*[
            Circle(radius=cell * 0.3, color=PURPLE_B, fill_opacity=0.2)
            for _ in range(3)
        ]).arrange(DOWN, buff=0.3)
        output_nodes.next_to(flattened_group, RIGHT, buff=1.5)
        self.play(FadeIn(output_nodes))

        # Flatten → Dense 연결선 (단순히 몇 개만)
        connections = VGroup()
        for i in range(0, len(flattened_group), max(1, len(flattened_group)//5)):
            for node in output_nodes:
                line = Line(flattened_group[i].get_right(), node.get_left(), stroke_color=GRAY, stroke_opacity=0.4)
                connections.add(line)
        self.play(Create(connections), run_time=1.2)
        self.wait(0.5)
        self.play(FadeOut(dense_label))

        # === (10) Softmax 단계 ===
        softmax_label = Text("Softmax", color=BLUE_B, font_size=30)
        softmax_label.next_to(output_nodes, UP, buff=0.4)
        self.play(Write(softmax_label))

        # 각 노드의 raw 출력값 (Dense 결과)
        import math
        fc_outputs = [random.uniform(-2, 2) for _ in range(3)]
        exp_vals = [math.exp(v) for v in fc_outputs]
        sum_exp = sum(exp_vals)
        softmax_vals = [e / sum_exp for e in exp_vals]

        # Softmax 막대 시각화
        softmax_bars = VGroup()
        for i, (node, val) in enumerate(zip(output_nodes, softmax_vals)):
            bar_height = 0.8 * val + 0.2
            bar = Rectangle(
                height=bar_height,
                width=0.35,
                fill_color=BLUE,
                fill_opacity=0.6,
                stroke_color=WHITE
            )
            bar.next_to(node, RIGHT, buff=0.4)
            softmax_bars.add(bar)
        self.play(TransformFromCopy(output_nodes, softmax_bars), run_time=1.2)
        self.wait(0.5)

        # 가장 큰 확률 강조
        max_idx = max(range(len(softmax_vals)), key=lambda i: softmax_vals[i])
        highlight_bar = softmax_bars[max_idx]

        # 나머지 막대 살짝 흐리게
        for i, bar in enumerate(softmax_bars):
            if i != max_idx:
                bar.set_fill(opacity=0.25)

        # 강조 애니메이션
        self.play(
            highlight_bar.animate.set_fill(color=YELLOW, opacity=0.9).scale(1.1),
            run_time=0.7
        )

        # 예측 클래스 라벨
        pred_label = Text(
            f"Predicted Class: {max_idx + 1}",
            font_size=28,
            color=YELLOW_B
        )
        pred_label.next_to(highlight_bar, RIGHT, buff=0.5)
        self.play(Write(pred_label))
        self.play(Indicate(highlight_bar, color=YELLOW), run_time=1.0)
        self.wait(1.2)



"""

    scene_code = scene_template.replace("__CFG_JSON__", json.dumps(cfg))

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp.write(scene_code)
        tmp_path = tmp.name

    cmd = ["manim", "-ql", tmp_path, "CNNParamScene", "--format", fmt, "-o", f"{out_basename}.{fmt}"]
    subprocess.run(cmd, check=True)

    video_path = MEDIA_DIR / f"{out_basename}.{fmt}"
    return str(video_path)
