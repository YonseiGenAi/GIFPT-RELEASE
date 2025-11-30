# video_render.py
import os
import time
import tempfile
import subprocess
import re
from pathlib import Path
import logging
import shutil

from studio.ai.llm_domain import call_llm_detect_domain
from studio.ai.llm import call_llm_domain_ir
from studio.ai.render_cnn_matrix import render_cnn_matrix
from studio.ai.llm_pseudocode import call_llm_pseudocode_ir, call_llm_sort_trace
from studio.ai.llm_anim_ir import call_llm_anim_ir
from studio.ai.llm_codegen import call_llm_codegen
from studio.ai.render_sorting import render_sorting

logger = logging.getLogger(__name__)

RESULT_DIR = Path(os.environ.get("GIFPT_RESULT_DIR", "/tmp/gifpt_results"))


def _sanitize_text(text: str) -> str:
    """main.py의 sanitize_text와 같은 역할 (간단한 공백/줄바꿈 정리)."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


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
        sort_trace = call_llm_sort_trace(user_text)
        video_path = render_sorting(sort_trace)
        logger.info("🎬 sorting video rendered at %s", video_path)
        return video_path

    # (3) 일반 알고리즘/모델 시각화 (pseudocode → anim_ir → anim_ir → manim 코드)
    pseudo_ir = call_llm_pseudocode_ir(user_text)
    anim_ir = call_llm_anim_ir(pseudo_ir)
    manim_code = call_llm_codegen(anim_ir)

    # 결과 저장 디렉터리 (/data/results/videos 등)
    output_dir = RESULT_DIR / "videos"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 🔹 manim용 베이스 이름 (확장자 없이)
    basename = f"video_{int(time.time())}"
    filename = f"{basename}.mp4"

    logger.info("🎬 rendering video (basename=%s) under %s", basename, output_dir)

    # manim 코드 임시 파일로 저장
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp.write(manim_code)
        tmp_path = tmp.name

    # Manim 실행 (AlgorithmScene 기준, main.py 로직과 동일한 구조)
    subprocess.run(
        [
            "manim",
            "-ql",
            tmp_path,
            "AlgorithmScene",
            "--format",
            "mp4",
            "-o",
            basename,        # ✅ 확장자 없는 베이스 이름만 넘기기
        ],
        cwd=output_dir,      # media 디렉터리 포함해서 output_dir 아래가 루트가 되도록
        check=True,
    )

    # 🔹 manim이 실제로 만든 mp4 파일 위치 찾기 (media/.../basename.mp4)
    candidates = list(output_dir.rglob(f"{basename}.mp4"))
    if not candidates:
        logger.error("❌ Manim finished but could not find %s.mp4 under %s", basename, output_dir)
        raise RuntimeError(f"Manim finished but could not find {basename}.mp4 under {output_dir}")

    src_path = candidates[0]

    # 🔹 우리가 약속한 최종 위치: output_dir / filename
    final_path = output_dir / filename
    if final_path.exists():
        final_path.unlink()

    # src_path가 이미 final_path이면 move 안 해도 되지만, 안전하게 한 번 정리
    if src_path.resolve() != final_path.resolve():
        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), final_path)

    logger.info("🎬 video rendered at %s", final_path)

    return str(final_path)
