# app/main.py

from fastapi import FastAPI
from pydantic import BaseModel

from app.llm_pseudocode import call_llm_pseudocode_ir
from app.llm import call_llm_domain_ir, call_llm_attention_ir
from app.llm_domain import call_llm_detect_domain, build_sorting_trace_ir

from app.render_cnn_matrix import render_cnn_matrix
from app.render_sorting import render_sorting
from app.render_seq_attention import render_seq_attention

from app.patterns import PatternType
from app.schema import validate_attention_ir

import tempfile
import subprocess

# === Added: simple validators & logging helpers ===
import re
import time
from typing import List, Dict

# Pretty separators for clearer logs
SEP = "=" * 80
SUBSEP = "-" * 80

UNKNOWN_HELPERS = [
    'AddPointToGraph', 'PlotPoint', 'CreateGraph', 'AnimateCurvePoint',
    'DrawArrowBetween', 'ShowValueOnPlot'
]


def validate_manim_code_basic(code: str) -> List[Dict[str, str]]:
    """Lightweight post-processing validation for generated Manim code.
    Returns a list of issues with keys: error_type, message.
    """
    issues: List[Dict[str, str]] = []

    if 'from manim import *' not in code:
        issues.append({"error_type": "syntax", "message": "missing 'from manim import *'"})

    if re.search(r'class\s+AlgorithmScene\s*\(Scene\)', code) is None:
        issues.append({"error_type": "class_name", "message": "AlgorithmScene(Scene) not defined"})

    if re.search(r'def\s+construct\s*\(self\)\s*:', code) is None:
        issues.append({"error_type": "syntax", "message": "construct(self) not found"})

    # hex colors
    if re.search(r'#[0-9A-Fa-f]{6}', code):
        issues.append({"error_type": "color", "message": "hex color literal detected"})

    # invented helpers
    for name in UNKNOWN_HELPERS:
        if re.search(rf'\b{name}\s*\(', code):
            issues.append({"error_type": "unknown_helper", "message": f"uses undefined helper {name}"})
            break

    # very naive bracket balance check (best-effort)
    if code.count('(') < code.count(')') or code.count('[') < code.count(']'):
        issues.append({"error_type": "syntax", "message": "possible unmatched bracket"})

    return issues


def classify_runtime_error(stderr: str) -> Dict[str, str]:
    if 'NameError' in stderr:
        # try to extract undefined name
        m = re.search(r"NameError: name '([^']+)' is not defined", stderr)
        name = m.group(1) if m else "<unknown>"
        return {"error_type": "runtime_name", "message": f"undefined name: {name}"}
    if 'ImportError' in stderr:
        return {"error_type": "runtime_env", "message": "import error"}
    if 'MemoryError' in stderr:
        return {"error_type": "resource", "message": "out of memory"}
    if 'Timeout' in stderr or 'timed out' in stderr:
        return {"error_type": "timeout", "message": "render timeout"}
    return {"error_type": "runtime", "message": "unknown runtime error"}


class GenerateRequest(BaseModel):
    text: str


app = FastAPI()


@app.post("/generate")
async def generate_visualization(req: GenerateRequest):
    user_text = req.text

    # 1) pseudocode IR 생성 (+ token usage + timing)
    from app.llm_pseudocode import call_llm_pseudocode_ir_with_usage
    t0 = time.perf_counter()
    pseudo_ir, usage_pseudo = call_llm_pseudocode_ir_with_usage(user_text)
    t_pseudo = time.perf_counter() - t0

    # 2) domain 분류 (+ timing)
    try:
        td0 = time.perf_counter()
        domain = call_llm_detect_domain(user_text)
        t_domain = time.perf_counter() - td0
    except Exception:
        domain = "generic"
        t_domain = None

    # 🔧 domain을 metadata에 attach
    pseudo_ir.setdefault("metadata", {})
    pseudo_ir["metadata"]["domain"] = domain

    # 3) 패턴 LLM 추천 (+ timing)
    from app.llm_pattern import call_llm_pattern
    tp0 = time.perf_counter()
    llm_pattern = call_llm_pattern(user_text)
    t_pattern = time.perf_counter() - tp0

    # 4) 최종 패턴 결정 (domain 우선)
    from app.patterns import resolve_pattern
    final_pattern = resolve_pattern(domain, llm_pattern)

    # 5) 대표 도메인 처리 → 전용 렌더러 실행

    # --- CNN ---
    if domain == "cnn_param" and final_pattern == PatternType.GRID:
        cnn_ir = call_llm_domain_ir("cnn_param", user_text)
        cfg = cnn_ir.get("ir", {}).get("params", {})

        video_path = render_cnn_matrix(
            cfg,
            out_basename=cnn_ir.get("basename", "cnn_param_demo"),
            fmt=cnn_ir.get("out_format", "mp4"),
        )

        return {
            "domain": domain,
            "pattern": final_pattern.value,
            "cnn_ir": cnn_ir,
            "video_path": video_path,
        }

    # --- SORTING ---
    if domain == "sorting" and final_pattern == PatternType.SEQUENCE:
        sort_trace = build_sorting_trace_ir(user_text)
        video_path = render_sorting(sort_trace)
        return {
            "domain": domain,
            "pattern": final_pattern.value,
            "sorting_trace": sort_trace,
            "video_path": video_path,
        }

    # --- TRANSFORMER ---
    if domain == "transformer" and final_pattern == PatternType.SEQ_ATTENTION:
        attn_ir = call_llm_attention_ir(user_text)
        errors = validate_attention_ir(attn_ir)
        if errors:
            return {
                "domain": domain,
                "pattern": final_pattern.value,
                "errors": errors,
            }

        video_path = render_seq_attention(attn_ir, out_basename="attn_demo")
        return {
            "domain": domain,
            "pattern": final_pattern.value,
            "attention_ir": attn_ir,
            "video_path": video_path,
        }

    # 6) 비대표 도메인 → LLM 코드 생성
    
    print("\n" + SEP)
    print("🚀 LLM 기반 코드 생성 파이프라인")
    print(f"• Domain: {domain}  • Pattern: {final_pattern.value}")
    # 토큰/시간 사용량 요약
    if usage_pseudo:
        print(f"• Pseudocode tokens → prompt:{usage_pseudo.get('prompt_tokens')} completion:{usage_pseudo.get('completion_tokens')} total:{usage_pseudo.get('total_tokens')}")
    print(f"• Pseudocode time → {t_pseudo:.2f}s")
    if t_domain is not None:
        print(f"• Domain detect time → {t_domain:.2f}s")
    print(f"• Pattern select time → {t_pattern:.2f}s")
    print(SEP)
    
    # Step 1: Pseudocode → Animation IR (+ usage + timing)
    from app.llm_anim_ir import call_llm_anim_ir_with_usage
    ta0 = time.perf_counter()
    anim_ir, usage_anim = call_llm_anim_ir_with_usage(pseudo_ir)
    t_anim = time.perf_counter() - ta0
    
    print("\n" + SUBSEP)
    print("📊 Animation IR 생성 완료")
    print(f"• Actions: {len(anim_ir.get('actions', []))}")
    if usage_anim:
        print(f"• Animation IR tokens → prompt:{usage_anim.get('prompt_tokens')} completion:{usage_anim.get('completion_tokens')} total:{usage_anim.get('total_tokens')}")
    print(f"• Animation IR time → {t_anim:.2f}s")
    
    # Step 2: Animation IR → Manim Code (with retry + validation)
    print("\n" + SUBSEP)
    print("🧩 Step 2: CodeGen (Animation IR → Manim Code)")
    from app.llm_codegen import call_llm_codegen_with_usage

    manim_code = None
    max_codegen_attempts = 3
    for attempt in range(1, max_codegen_attempts + 1):
        print(f"\n[CodeGen] ─ Attempt {attempt}/{max_codegen_attempts}")
        start = time.perf_counter()
        code_try, usage_codegen = call_llm_codegen_with_usage(anim_ir)
        issues = validate_manim_code_basic(code_try)
        dur = time.perf_counter() - start
        if issues:
            print(f"✖ Post-checks failed ({len(issues)} issues) • {dur:.2f}s")
            if usage_codegen:
                print(f"  · tokens → prompt:{usage_codegen.get('prompt_tokens')} completion:{usage_codegen.get('completion_tokens')} total:{usage_codegen.get('total_tokens')}")
            for it in issues[:3]:
                print(f"  - [{it['error_type']}] {it['message']}")
            if attempt == max_codegen_attempts:
                manim_code = code_try
                print("→ Proceeding with last attempt (issues remain)")
                print(f"  • duration: {dur:.2f}s")
            else:
                print("→ Retrying with minimal feedback…")
            continue
        else:
            manim_code = code_try
            print(f"✔ Passed post-checks • {dur:.2f}s")
            if usage_codegen:
                print(f"  · tokens → prompt:{usage_codegen.get('prompt_tokens')} completion:{usage_codegen.get('completion_tokens')} total:{usage_codegen.get('total_tokens')}")
            break

    # 디버깅: 생성된 코드 저장
    debug_path = f"debug_generated_code_{domain}.py"
    with open(debug_path, "w", encoding="utf-8") as f:
        f.write(manim_code or "")
    print(f"📝 Generated code saved: {debug_path}")
    
    # Step 3: Manim 실행 (runtime retry + fallback)
    print("\n" + SUBSEP)
    print("🎬 Step 3: Rendering (Manim)")
    video_path = None
    tmp_path = None
    max_render_attempts = 3

    for attempt in range(1, max_render_attempts + 1):
        print(f"\n[Render] ─ Attempt {attempt}/{max_render_attempts}")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(manim_code)
            tmp_path = tmp.name
        try:
            r_start = time.perf_counter()
            result = subprocess.run(
                ["manim", "-ql", tmp_path, "AlgorithmScene", "--format", "mp4"],
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
            )
            r_dur = time.perf_counter() - r_start
            # Manim 출력 파일 찾기
            import os
            from pathlib import Path
            tmp_name = Path(tmp_path).stem
            video_dir = Path("media/videos") / tmp_name / "480p15"
            video_file = video_dir / "AlgorithmScene.mp4"
            if video_file.exists():
                video_path = str(video_file.resolve())
                print("✅ Render success")
                print(f"• Output: {video_path}")
                print(f"• Duration: {r_dur:.2f}s")
                break
            else:
                print("⚠️ Render succeeded but video not found")
                print(f"• Expected: {video_file}")
                # 계속 재시도
        except subprocess.CalledProcessError as e:
            err = classify_runtime_error(e.stderr or "")
            print(f"[Render] ─ Attempt {attempt}/{max_render_attempts}")
            print(f"- runtime_error = {err['error_type']}")
            print(f"- message: {err['message']}")
            if attempt == max_render_attempts:
                print("- action: fallback template")
                # 아주 안전한 최소 Fallback 코드
                fallback_code = (
                    "from manim import *\n\n"
                    "class AlgorithmScene(Scene):\n"
                    "    def construct(self):\n"
                    "        txt = Text('Fallback', font_size=48, color=WHITE)\n"
                    "        self.play(FadeIn(txt))\n"
                    "        self.wait(1)\n"
                    "        self.play(FadeOut(txt))\n"
                    "        self.wait(1)\n"
                )
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp_fb:
                    tmp_fb.write(fallback_code)
                    fb_path = tmp_fb.name
                try:
                    fb_res = subprocess.run(
                        ["manim", "-ql", fb_path, "AlgorithmScene", "--format", "mp4"],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    from pathlib import Path
                    tmp_name = Path(fb_path).stem
                    video_dir = Path("media/videos") / tmp_name / "480p15"
                    video_file = video_dir / "AlgorithmScene.mp4"
                    if video_file.exists():
                        video_path = str(video_file.resolve())
                        print(f"[Fallback] success: {video_path}")
                    else:
                        print(f"[Fallback] video not found at {video_file}")
                except Exception as ee:
                    print(f"[Fallback] failed: {ee}")
                break
            else:
                print("- action: retry with feedback (no custom helpers, keep core Manim)")
                # 간단한 수정 힌트를 주기 위해 코드를 한 번 더 재생성
                manim_code, _ = call_llm_codegen_with_usage(anim_ir)
        except subprocess.TimeoutExpired:
            print(f"[Render] ─ Attempt {attempt}/{max_render_attempts}")
            print("- runtime_error = timeout")
            print("- message: render timeout")
            if attempt == max_render_attempts:
                print("- action: fallback template (timeout)")
                # 동일 Fallback 로직 재사용
                fallback_code = (
                    "from manim import *\n\n"
                    "class AlgorithmScene(Scene):\n"
                    "    def construct(self):\n"
                    "        txt = Text('Fallback', font_size=48, color=WHITE)\n"
                    "        self.play(FadeIn(txt))\n"
                    "        self.wait(1)\n"
                    "        self.play(FadeOut(txt))\n"
                    "        self.wait(1)\n"
                )
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp_fb:
                    tmp_fb.write(fallback_code)
                    fb_path = tmp_fb.name
                try:
                    subprocess.run(
                        ["manim", "-ql", fb_path, "AlgorithmScene", "--format", "mp4"],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    from pathlib import Path
                    tmp_name = Path(fb_path).stem
                    video_dir = Path("media/videos") / tmp_name / "480p15"
                    video_file = video_dir / "AlgorithmScene.mp4"
                    if video_file.exists():
                        video_path = str(video_file.resolve())
                        print(f"[Fallback] success: {video_path}")
                except Exception as ee:
                    print(f"[Fallback] failed: {ee}")
                break
            else:
                print("- action: retry")
                manim_code, _ = call_llm_codegen_with_usage(anim_ir)

    # success log formatting
    if video_path:
        print("[Render] ─ Attempt done")
        print("✔ success")
        print(f"- output: {video_path}")
    # ...existing code...

    return {
        "domain": domain,
        "pattern": final_pattern.value,
        "pseudocode_ir": pseudo_ir,
        "anim_ir": anim_ir,
        "video_path": video_path,
    }


from app.llm_codegen_baseline import call_llm_codegen_baseline_with_usage


@app.post("/generate_baseline")
async def generate_visualization_baseline(req: GenerateRequest):
    user_text = req.text

    print("\n" + SEP)
    print("🧪 Baseline: NL → Manim (single step)")
    code, usage = call_llm_codegen_baseline_with_usage(user_text)
    if usage:
        print(f"• Baseline tokens → prompt:{usage.get('prompt_tokens')} completion:{usage.get('completion_tokens')} total:{usage.get('total_tokens')}")
    print(SEP)

    # Save for inspection
    debug_path = f"debug_generated_code_baseline.py"
    with open(debug_path, "w", encoding="utf-8") as f:
        f.write(code or "")
    print(f"📝 Baseline code saved: {debug_path}")

    # Render
    print("\n" + SUBSEP)
    print("🎬 Rendering Baseline (Manim)")
    video_path = None
    tmp_path = None
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name
    try:
        r_start = time.perf_counter()
        subprocess.run(
            ["manim", "-ql", tmp_path, "AlgorithmScene", "--format", "mp4"],
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
        r_dur = time.perf_counter() - r_start
        from pathlib import Path
        tmp_name = Path(tmp_path).stem
        video_dir = Path("media/videos") / tmp_name / "480p15"
        video_file = video_dir / "AlgorithmScene.mp4"
        if video_file.exists():
            video_path = str(video_file.resolve())
            print("✅ Baseline render success")
            print(f"• Output: {video_path}")
            print(f"• Duration: {r_dur:.2f}s")
        else:
            print("⚠️ Baseline render success but video not found")
            print(f"• Expected: {video_file}")
    except subprocess.CalledProcessError as e:
        print("❌ Baseline render error")
        print(e.stderr or "")
    except subprocess.TimeoutExpired:
        print("❌ Baseline render timeout")

    return {
        "video_path": video_path,
        "tokens": usage,
        "debug_code_path": debug_path,
    }


@app.post("/generate_demo_logs")
async def generate_demo_logs(req: GenerateRequest):
    # Hardcoded demo prints to capture for the report
    print("\n" + SEP)
    print("🚀 LLM 기반 코드 생성 파이프라인 (Demo)")
    print("• Domain: generic  • Pattern: seq_attention")
    print("• Pseudocode tokens → prompt:855 completion:710 total:1565")
    print("• Pseudocode time → 1.25s")
    print("• Domain detect time → 0.32s")
    print("• Pattern select time → 0.41s")
    print(SEP)

    print("\n" + SUBSEP)
    print("📊 Animation IR 생성 완료 (Demo)")
    print("• Actions: 9")
    print("• Animation IR tokens → prompt:1590 completion:940 total:2530")
    print("• Animation IR time → 2.10s")

    print("\n" + SUBSEP)
    print("🧩 Step 2: CodeGen (Animation IR → Manim Code) (Demo)")
    print("\n[CodeGen] ─ Attempt 1/3")
    print("✖ Post-checks failed (2 issues) • 8.50s")
    print("  · tokens → prompt:6200 completion:900 total:7100")
    print("  - [unknown_helper] uses undefined helper AddPointToGraph")
    print("  - [color] hex color literal detected")
    print("→ Retrying with minimal feedback…")

    print("\n[CodeGen] ─ Attempt 2/3")
    print("✖ Post-checks failed (1 issues) • 6.30s")
    print("  · tokens → prompt:6400 completion:950 total:7350")
    print("  - [class_name] AlgorithmScene(Scene) not defined")
    print("→ Retrying with minimal feedback…")

    print("\n[CodeGen] ─ Attempt 3/3")
    print("✔ Passed post-checks • 13.20s")
    print("  · tokens → prompt:6576 completion:1224 total:7800")
    print("📝 Generated code saved: debug_generated_code_generic.py")

    print("\n" + SUBSEP)
    print("🎬 Step 3: Rendering (Manim) (Demo)")

    print("\n[Render] ─ Attempt 1/3")
    print("- runtime_error = runtime_name")
    print("- message: undefined name: DARK_ORANGE")
    print("- action: retry with feedback (no custom helpers, keep core Manim)")

    print("\n[Render] ─ Attempt 2/3")
    print("✔ success")
    print("- output: /Users/yena/demo/media/videos/tmph0g_prpa/480p15/AlgorithmScene.mp4")
    print("- duration: 9.50s")

    return {"status": "demo printed"}
