# video_render.py
import os
import time
import tempfile
import subprocess
import re
from pathlib import Path
import logging

from studio.ai.llm_domain import call_llm_detect_domain
from studio.ai.llm import call_llm_domain_ir
from studio.ai.render_cnn_matrix import render_cnn_matrix
from studio.ai.render_sorting import render_sorting
from studio.ai.llm_domain import build_sorting_trace_ir

logger = logging.getLogger(__name__)

RESULT_DIR = Path(os.environ.get("GIFPT_RESULT_DIR", "/tmp/gifpt_results"))

SEP = "=" * 80
SUBSEP = "-" * 80

UNKNOWN_HELPERS = [
    'AddPointToGraph', 'PlotPoint', 'CreateGraph', 'AnimateCurvePoint',
    'DrawArrowBetween', 'ShowValueOnPlot'
]

def _sanitize_text(text: str) -> str:
    """main.py의 sanitize_text와 같은 역할 (간단한 공백/줄바꿈 정리)."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def validate_manim_code_basic(code: str):
    """LLM이 만든 Manim 코드에 대한 경량 검증"""
    issues = []

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

    # 매우 단순한 괄호 체크
    if code.count('(') < code.count(')') or code.count('[') < code.count(']'):
        issues.append({"error_type": "syntax", "message": "possible unmatched bracket"})

    return issues


def classify_runtime_error(stderr: str):
    if 'NameError' in stderr:
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



_FALLBACK_CODE = (
    "from manim import *\n\n"
    "class AlgorithmScene(Scene):\n"
    "    def construct(self):\n"
    "        txt = Text('Fallback', font_size=48, color=WHITE)\n"
    "        self.play(FadeIn(txt))\n"
    "        self.wait(1)\n"
    "        self.play(FadeOut(txt))\n"
    "        self.wait(1)\n"
)


def run_manim_code(code: str, output_dir: Path, output_name: str | None = None) -> str:
    """Render Manim code with retry and fallback.

    Args:
        code: Complete Manim Python source (must define AlgorithmScene).
        output_dir: Directory to use as Manim's working directory.
        output_name: Base filename for the output mp4 (default: auto-generated).

    Returns:
        Absolute path to the rendered mp4 file.

    Raises:
        RuntimeError: If both primary render and fallback render fail.
    """
    import time as _time

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if output_name is None:
        output_name = f"video_{int(_time.time())}.mp4"

    video_path = None
    max_render_attempts = 3

    for attempt in range(1, max_render_attempts + 1):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            subprocess.run(
                [
                    "manim", "-ql",
                    tmp_path,
                    "AlgorithmScene",
                    "--format", "mp4",
                    "-o", output_name,
                ],
                cwd=output_dir,
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
            )

            tmp_name = Path(tmp_path).stem
            candidate = output_dir / "media" / "videos" / tmp_name / "480p15" / output_name
            if candidate.exists():
                video_path = str(candidate.resolve())
                break

            matches = list(output_dir.rglob(output_name))
            if matches:
                video_path = str(matches[0].resolve())
                break

        except subprocess.CalledProcessError as e:
            err = classify_runtime_error(e.stderr or "")
            logger.warning("run_manim_code attempt %d/%d failed: %s", attempt, max_render_attempts, err)
            if attempt == max_render_attempts:
                break

        except subprocess.TimeoutExpired:
            logger.warning("run_manim_code attempt %d/%d timed out", attempt, max_render_attempts)
            if attempt == max_render_attempts:
                break

    if video_path:
        return video_path

    # Fallback: render a minimal placeholder scene
    logger.warning("run_manim_code: all attempts failed, rendering fallback")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp_fb:
        tmp_fb.write(_FALLBACK_CODE)
        fb_path = tmp_fb.name
    try:
        subprocess.run(
            [
                "manim", "-ql",
                fb_path,
                "AlgorithmScene",
                "--format", "mp4",
                "-o", output_name,
            ],
            cwd=output_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        fb_name = Path(fb_path).stem
        fb_candidate = output_dir / "media" / "videos" / fb_name / "480p15" / output_name
        if fb_candidate.exists():
            return str(fb_candidate.resolve())
        matches = list(output_dir.rglob(output_name))
        if matches:
            return str(matches[0].resolve())
    except Exception as ee:
        raise RuntimeError(f"run_manim_code fallback failed: {ee}") from ee

    raise RuntimeError("run_manim_code: video file not found after fallback render")


def render_video_from_instructions(instructions: str) -> str:
    """
    PDF 분석 파이프라인에서 전달된 'video instructions' 텍스트를 받아
    main.py의 /generate 로직과 동일한 파이프라인으로 영상을 생성한다.

    - cnn_param  → call_llm_domain_ir + render_cnn_matrix
    - sorting    → call_llm_sort_trace + render_sorting
    - 기타       → pseudocode_ir → anim_ir → manim_code → manim 실행
    """
    user_text = _sanitize_text(instructions)

    # 1) 도메인 결정
    domain = call_llm_detect_domain(user_text)
    logger.info("🎯 detected domain for video_render: %s", domain)

    # 2) 도메인별 처리 -----------------------------

    # (1) CNN 파라미터 전용
    if domain == "cnn_param":
        ir = call_llm_domain_ir("cnn_param", user_text)
        params = ir["ir"]["params"]

        video_path = render_cnn_matrix(params)
        logger.info("🎬 CNN video rendered at %s", video_path)
        return video_path

    # (2) 정렬 전용 파이프라인 (trace → render_sorting)
    if domain == "sorting":
        sort_trace = build_sorting_trace_ir(user_text)
        video_path = render_sorting(sort_trace)
        logger.info("🎬 sorting video rendered at %s", video_path)
        return video_path

        # 3) 일반 알고리즘/모델 시각화 (pseudocode → anim_ir → manim 코드)
    #    main.py의 고급 로직 이식

    print("\n" + SEP)
    print("🚀 LLM 기반 코드 생성 파이프라인 (Django worker)")
    print(f"• Domain: {domain}")
    # 1단계: pseudocode IR + usage
    from studio.ai.llm_pseudocode import call_llm_pseudocode_ir_with_usage
    t0 = time.perf_counter()
    pseudo_ir, usage_pseudo = call_llm_pseudocode_ir_with_usage(user_text)
    t_pseudo = time.perf_counter() - t0

    if usage_pseudo:
        print(f"• Pseudocode tokens → prompt:{usage_pseudo.get('prompt_tokens')} "
              f"completion:{usage_pseudo.get('completion_tokens')} "
              f"total:{usage_pseudo.get('total_tokens')}")
    print(f"• Pseudocode time → {t_pseudo:.2f}s")
    print(SEP)

    # 2단계: Animation IR
    from studio.ai.llm_anim_ir import call_llm_anim_ir_with_usage
    ta0 = time.perf_counter()
    anim_ir, usage_anim = call_llm_anim_ir_with_usage(pseudo_ir)
    t_anim = time.perf_counter() - ta0

    print("\n" + SUBSEP)
    print("📊 Animation IR 생성 완료")
    print(f"• Actions: {len(anim_ir.get('actions', []))}")
    if usage_anim:
        print(f"• Animation IR tokens → prompt:{usage_anim.get('prompt_tokens')} "
              f"completion:{usage_anim.get('completion_tokens')} "
              f"total:{usage_anim.get('total_tokens')}")
    print(f"• Animation IR time → {t_anim:.2f}s")

    # 3단계: Animation IR → Manim 코드 (리트라이 + post-check)
    print("\n" + SUBSEP)
    print("🧩 Step 2: CodeGen (Animation IR → Manim Code)")
    from studio.ai.llm_codegen import call_llm_codegen_with_usage

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
                print(f"  · tokens → prompt:{usage_codegen.get('prompt_tokens')} "
                      f"completion:{usage_codegen.get('completion_tokens')} "
                      f"total:{usage_codegen.get('total_tokens')}")
            for it in issues[:3]:
                print(f"  - [{it['error_type']}] {it['message']}")
            if attempt == max_codegen_attempts:
                manim_code = code_try
                print("→ Proceeding with last attempt (issues remain)")
            else:
                print("→ Retrying with minimal feedback…")
            continue
        else:
            manim_code = code_try
            print(f"✔ Passed post-checks • {dur:.2f}s")
            if usage_codegen:
                print(f"  · tokens → prompt:{usage_codegen.get('prompt_tokens')} "
                      f"completion:{usage_codegen.get('completion_tokens')} "
                      f"total:{usage_codegen.get('total_tokens')}")
            break

    # 디버깅용 코드 저장 (best-effort)
    debug_dir = Path(os.environ.get("GIFPT_RESULT_DIR", "/tmp/gifpt_results"))
    debug_path = debug_dir / f"debug_generated_code_{domain}.py"
    try:
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(manim_code or "", encoding="utf-8")
        print(f"📝 Generated code saved: {debug_path}")
    except Exception:
        pass

    # 4단계: Manim 렌더링 (리트라이 + fallback)
    print("\n" + SUBSEP)
    print("🎬 Step 3: Rendering (Manim)")
    output_dir = RESULT_DIR / "videos"
    output_name = f"video_{int(time.time())}.mp4"
    video_path = run_manim_code(manim_code, output_dir, output_name)
    logger.info("🎬 video rendered at %s", video_path)
    return video_path
