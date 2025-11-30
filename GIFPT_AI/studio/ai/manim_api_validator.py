"""
Manim API Validator
LLM이 생성하려는 코드가 유효한 Manim API인지 사전 검증
"""
import ast
import inspect
from typing import List, Dict, Any

# Manim에서 허용되는 API 화이트리스트
VALID_MANIM_CLASSES = {
    # Mobjects
    "Square", "Circle", "Rectangle", "Line", "Arrow", "Dot",
    "Text", "MathTex", "Tex",
    "VGroup", "VMobject",
    
    # Animations
    "FadeIn", "FadeOut", "Create", "Write", "Uncreate", "Unwrite",
    "Transform", "ReplacementTransform", "TransformFromCopy",
    "Indicate", "Circumscribe", "Flash", "FocusOn", "ShowPassingFlash",
    "GrowFromCenter", "GrowFromPoint", "GrowFromEdge",
    "ShrinkToCenter",
    
    # Layout
    "SurroundingRectangle",
    
    # Colors (constants)
    "WHITE", "BLACK", "BLUE", "BLUE_B", "BLUE_C", "BLUE_D", "BLUE_E",
    "GREEN", "GREEN_B", "GREEN_C", "GREEN_D", "GREEN_E",
    "RED", "RED_B", "RED_C", "RED_D", "RED_E",
    "YELLOW", "YELLOW_B", "YELLOW_C", "YELLOW_D", "YELLOW_E",
    "PURPLE", "PURPLE_B", "PURPLE_C", "PURPLE_D", "PURPLE_E",
    "GRAY", "GRAY_B", "GRAY_C", "GRAY_D", "GRAY_E",
    "ORANGE", "PINK", "TEAL", "MAROON",
    
    # Directions
    "UP", "DOWN", "LEFT", "RIGHT", "IN", "OUT",
    "UL", "UR", "DL", "DR",
}

INVALID_MANIM_CLASSES = {
    "Highlight", "Focus", "Emphasize", "FocusOn",  # 존재하지 않는 애니메이션
    "MobjectTable", "IntegerTable", "DecimalTable",  # 존재하지 않는 테이블
    "ImageMobject", "SVGMobject",  # 파일 의존성
    "VIOLET", "INDIGO", "CYAN", "MAGENTA", "BROWN",  # 잘못된 색상
}


def validate_manim_code(code: str) -> Dict[str, Any]:
    """
    생성된 Manim 코드를 파싱해서 유효성 검증
    
    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str]
        }
    """
    errors = []
    warnings = []
    
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {
            "valid": False,
            "errors": [f"Syntax error: {e}"],
            "warnings": []
        }
    
    # AST를 순회하며 클래스/함수 호출 검사
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            name = node.id
            
            # 잘못된 API 사용 체크
            if name in INVALID_MANIM_CLASSES:
                errors.append(f"Invalid Manim class/constant: {name}")
            
            # 유효하지 않은 색상 체크
            if name.startswith("LIGHT_") or name.startswith("DARK_"):
                if name not in VALID_MANIM_CLASSES:
                    errors.append(f"Invalid color: {name} (use {name.replace('LIGHT_', '').replace('DARK_', '')}_B or _D instead)")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def suggest_fix(error: str) -> str:
    """오류에 대한 자동 수정 제안"""
    
    if "Highlight" in error:
        return "Replace with: obj.animate.set_fill(YELLOW, opacity=0.5) or Indicate(obj)"
    
    if "MobjectTable" in error:
        return "Replace with: VGroup(*[Square() for _ in range(n)]).arrange_in_grid()"
    
    if "VIOLET" in error:
        return "Replace with: PURPLE"
    
    if "CYAN" in error:
        return "Replace with: TEAL or BLUE_B"
    
    return "Check Manim documentation for valid alternatives"


# === LLM과 통합 ===

def validate_and_fix_generated_code(code: str, max_retries: int = 3) -> str:
    """
    생성된 코드를 검증하고, 오류가 있으면 자동 수정 시도
    """
    
    for attempt in range(max_retries):
        validation = validate_manim_code(code)
        
        if validation["valid"]:
            print(f"✅ Code validation passed (attempt {attempt + 1})")
            return code
        
        print(f"⚠️ Validation errors found (attempt {attempt + 1}):")
        for error in validation["errors"]:
            print(f"  - {error}")
            print(f"    Suggestion: {suggest_fix(error)}")
        
        # 간단한 자동 수정 시도
        for error in validation["errors"]:
            if "Highlight" in error:
                code = code.replace("Highlight(", "Indicate(")
            if "VIOLET" in error:
                code = code.replace("VIOLET", "PURPLE")
            if "CYAN" in error:
                code = code.replace("CYAN", "TEAL")
    
    print(f"❌ Validation failed after {max_retries} attempts")
    return code  # 최선을 다했으니 그냥 반환


if __name__ == "__main__":
    # 테스트
    test_code = """
from manim import *

class TestScene(Scene):
    def construct(self):
        square = Square(color=VIOLET)
        self.play(Highlight(square))
    """
    
    result = validate_manim_code(test_code)
    print(result)
