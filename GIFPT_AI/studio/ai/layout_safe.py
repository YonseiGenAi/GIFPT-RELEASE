"""
Safe Layout Helpers for Manim
LLM이 직접 좌표 계산하지 않고, 이 함수들을 사용하도록 강제
"""
from typing import List, Tuple, Dict
from manim import *
import numpy as np

# === 화면 안전 영역 (Manim 기본 해상도 기준) ===
SAFE_BOUNDS = {
    "xmin": -6.5,
    "xmax": 6.5,
    "ymin": -3.5,
    "ymax": 3.5
}


def layout_row_safe(n_items: int, item_width: float = 0.8, max_width: float = 12.0) -> List[Tuple[float, float, float]]:
    """
    n개의 요소를 가로로 안전하게 배치
    
    Args:
        n_items: 배치할 요소 개수
        item_width: 각 요소의 너비
        max_width: 최대 너비 (화면을 넘지 않도록)
    
    Returns:
        [(x, y, z), ...] 좌표 리스트
    """
    # 자동 스케일링: 요소가 많으면 간격 줄임
    total_width = n_items * item_width
    if total_width > max_width:
        item_width = max_width / n_items  # 자동 축소
    
    gap = item_width * 0.1  # 10% 간격
    total = (item_width + gap) * n_items - gap
    start_x = -total / 2
    
    positions = []
    for i in range(n_items):
        x = start_x + i * (item_width + gap) + item_width / 2
        # 화면 밖으로 나가면 강제로 클램핑
        x = np.clip(x, SAFE_BOUNDS["xmin"] + item_width/2, SAFE_BOUNDS["xmax"] - item_width/2)
        positions.append((x, 0.0, 0.0))
    
    return positions


def layout_grid_safe(n_rows: int, n_cols: int, cell_size: float = 0.5) -> List[List[Tuple[float, float, float]]]:
    """
    n_rows x n_cols 그리드를 안전하게 배치
    
    Returns:
        2D 리스트: [[row0 positions], [row1 positions], ...]
    """
    # 자동 스케일링
    max_grid_width = SAFE_BOUNDS["xmax"] * 2 - 2  # 좌우 여백 1씩
    max_grid_height = SAFE_BOUNDS["ymax"] * 2 - 2
    
    if n_cols * cell_size > max_grid_width:
        cell_size = max_grid_width / n_cols
    
    if n_rows * cell_size > max_grid_height:
        cell_size = min(cell_size, max_grid_height / n_rows)
    
    gap = cell_size * 0.05
    total_width = n_cols * (cell_size + gap) - gap
    total_height = n_rows * (cell_size + gap) - gap
    
    start_x = -total_width / 2
    start_y = total_height / 2
    
    grid_positions = []
    for row in range(n_rows):
        row_positions = []
        for col in range(n_cols):
            x = start_x + col * (cell_size + gap) + cell_size / 2
            y = start_y - row * (cell_size + gap) - cell_size / 2
            row_positions.append((x, y, 0.0))
        grid_positions.append(row_positions)
    
    return grid_positions


def layout_vertical_stack(n_items: int, item_height: float = 1.0, spacing: float = 0.5) -> List[Tuple[float, float, float]]:
    """
    n개의 요소를 세로로 안전하게 배치
    """
    max_height = SAFE_BOUNDS["ymax"] * 2 - 2
    total_height = n_items * item_height + (n_items - 1) * spacing
    
    if total_height > max_height:
        # 자동 축소
        scale = max_height / total_height
        item_height *= scale
        spacing *= scale
    
    start_y = (n_items - 1) * (item_height + spacing) / 2
    
    positions = []
    for i in range(n_items):
        y = start_y - i * (item_height + spacing)
        positions.append((0.0, y, 0.0))
    
    return positions


def layout_attention_heads(n_heads: int, tokens_per_head: int) -> List[Tuple[float, float, float]]:
    """
    Multi-head attention 레이아웃 (위 이미지 같은 경우)
    
    Args:
        n_heads: Attention head 개수
        tokens_per_head: 각 head의 토큰 개수
    
    Returns:
        각 head의 중심 좌표
    """
    # Head 간 수직 간격
    head_height = 1.5
    total_height = n_heads * head_height
    
    if total_height > SAFE_BOUNDS["ymax"] * 2 - 2:
        head_height = (SAFE_BOUNDS["ymax"] * 2 - 2) / n_heads
    
    start_y = (n_heads - 1) * head_height / 2
    
    positions = []
    for i in range(n_heads):
        y = start_y - i * head_height
        positions.append((0.0, y, 0.0))
    
    return positions


def layout_multihead_attention(
    n_heads: int, 
    tokens_per_head: int, 
    token_size: float = 0.4
) -> List[Dict[str, any]]:
    """
    Multi-head Attention 전용 레이아웃 (위 이미지처럼)
    
    Args:
        n_heads: Head 개수 (예: 3)
        tokens_per_head: 각 head의 토큰 수 (예: 6)
        token_size: 토큰 사각형 크기
    
    Returns:
        [{
            "head_id": 0,
            "head_center": (x, y, z),
            "token_positions": [(x, y, z), ...],
            "label_position": (x, y, z)
        }, ...]
    """
    # 화면 세로 영역을 head 개수로 나눔
    available_height = SAFE_BOUNDS["ymax"] * 2 - 3  # 위아래 여백
    head_height = available_height / n_heads
    
    # Head가 너무 많으면 토큰 크기 축소
    if head_height < tokens_per_head * token_size * 0.4:
        token_size = head_height / (tokens_per_head * 0.5)
    
    start_y = (n_heads - 1) * head_height / 2
    
    layouts = []
    for head_idx in range(n_heads):
        # Head 중심 Y 좌표
        head_y = start_y - head_idx * head_height
        
        # 토큰들을 가로로 배치
        token_positions = layout_row_safe(
            n_items=tokens_per_head, 
            item_width=token_size
        )
        # Y 좌표를 head_y로 이동
        token_positions = [(x, head_y, 0) for x, y, z in token_positions]
        
        # 라벨은 왼쪽에
        label_pos = (SAFE_BOUNDS["xmin"] + 1.5, head_y, 0)
        
        layouts.append({
            "head_id": head_idx,
            "head_center": (0, head_y, 0),
            "token_positions": token_positions,
            "label_position": label_pos
        })
    
    return layouts


def ensure_on_screen(obj, margin: float = 0.5) -> None:
    """
    Manim 객체가 화면 밖으로 나갔는지 체크하고 강제로 안으로 이동
    
    Args:
        obj: Manim Mobject
        margin: 화면 가장자리로부터 최소 거리
    """
    center = obj.get_center()
    width = obj.width
    height = obj.height
    
    # 좌표 클램핑
    new_x = np.clip(
        center[0], 
        SAFE_BOUNDS["xmin"] + width/2 + margin,
        SAFE_BOUNDS["xmax"] - width/2 - margin
    )
    new_y = np.clip(
        center[1],
        SAFE_BOUNDS["ymin"] + height/2 + margin,
        SAFE_BOUNDS["ymax"] - height/2 - margin
    )
    
    if new_x != center[0] or new_y != center[1]:
        obj.move_to([new_x, new_y, 0])
        print(f"⚠️ Object moved to stay on screen: {center} -> {[new_x, new_y, 0]}")


def check_overlap(obj1, obj2, threshold: float = 0.1) -> bool:
    """
    두 객체가 겹치는지 체크
    
    Returns:
        True if overlapping
    """
    c1 = obj1.get_center()
    c2 = obj2.get_center()
    
    dist = np.linalg.norm(c1 - c2)
    min_dist = (obj1.width + obj2.width) / 2 + threshold
    
    return dist < min_dist
