from manim import *
from typing import List, Tuple, Dict, Optional

# === 1. 기본 색상 / 스타일 프리셋 ===

NODE_FILL_COLOR = BLUE_E
NODE_STROKE_COLOR = WHITE
NODE_TEXT_COLOR = WHITE

LABEL_COLOR = GRAY_B
HIGHLIGHT_COLOR = YELLOW

DEFAULT_NODE_WIDTH = 1.2
DEFAULT_NODE_HEIGHT = 0.6
DEFAULT_NODE_RADIUS = 0.3

H_GAP = 1.2  # 가로 간격
V_GAP = 0.8  # 세로 간격


# === 2. 노드 생성 유틸 ===

def create_box_node(
    text: str,
    width: float = DEFAULT_NODE_WIDTH,
    height: float = DEFAULT_NODE_HEIGHT,
    fill_color = NODE_FILL_COLOR,
    stroke_color = NODE_STROKE_COLOR,
    text_color = NODE_TEXT_COLOR,
    font_size: int = 24,
) -> VGroup:
    """텍스트가 들어간 직사각형 노드 하나 생성."""
    box = Rectangle(
        width=width,
        height=height,
        stroke_color=stroke_color,
        fill_color=fill_color,
        fill_opacity=0.3,
    )
    label = Text(text, font_size=font_size, color=text_color)
    label.move_to(box.get_center())
    return VGroup(box, label)


def create_circle_node(
    text: str,
    radius: float = DEFAULT_NODE_RADIUS,
    fill_color = NODE_FILL_COLOR,
    stroke_color = NODE_STROKE_COLOR,
    text_color = NODE_TEXT_COLOR,
    font_size: int = 24,
) -> VGroup:
    """텍스트가 들어간 원형 노드 하나 생성."""
    circ = Circle(
        radius=radius,
        stroke_color=stroke_color,
        fill_color=fill_color,
        fill_opacity=0.3,
    )
    label = Text(text, font_size=font_size, color=text_color)
    label.move_to(circ.get_center())
    return VGroup(circ, label)


# === 3. 레이아웃 배치 유틸 ===

def layout_row(nodes: List[VGroup], center: np.ndarray = ORIGIN, gap: float = H_GAP) -> VGroup:
    """노드 리스트를 가로로 일렬 배치."""
    group = VGroup(*nodes)
    group.arrange(RIGHT, buff=gap)
    group.move_to(center)
    return group


def layout_column(nodes: List[VGroup], center: np.ndarray = ORIGIN, gap: float = V_GAP) -> VGroup:
    """노드 리스트를 세로로 일렬 배치."""
    group = VGroup(*nodes)
    group.arrange(DOWN, buff=gap)
    group.move_to(center)
    return group


def layout_grid(
    nodes: List[VGroup],
    rows: int,
    cols: int,
    center: np.ndarray = ORIGIN,
    h_gap: float = H_GAP,
    v_gap: float = V_GAP,
) -> VGroup:
    """노드 리스트를 rows x cols 격자 배치."""
    group = VGroup(*nodes)
    group.arrange_in_grid(rows=rows, cols=cols, buff=(v_gap, h_gap))
    group.move_to(center)
    return group


# === 4. Transformer 전용 레이아웃 템플릿 ===

TRANSFORMER_LAYOUT_TEMPLATE: Dict[str, Dict] = {
    "input_sentence": {"shape": "box", "pos": LEFT * 5 + UP * 3},
    "tokenizer": {"shape": "box", "pos": LEFT * 3 + UP * 3},
    "embedding": {"shape": "box", "pos": LEFT * 1 + UP * 3},
    "positional_encoding": {"shape": "box", "pos": RIGHT * 1 + UP * 3},
    "encoder_block": {"shape": "box", "pos": RIGHT * 3 + UP * 3},
    "self_attention": {"shape": "box", "pos": ORIGIN + UP * 0.5},
    "ffn": {"shape": "box", "pos": ORIGIN + DOWN * 1.2},
    "logits": {"shape": "box", "pos": RIGHT * 4 + DOWN * 1},
    "softmax": {"shape": "box", "pos": RIGHT * 6 + DOWN * 1},
}


def build_transformer_nodes() -> Dict[str, VGroup]:
    """Transformer 구조용 고정 노드들을 생성하여 dict로 반환."""
    nodes = {}

    nodes["input_sentence"] = create_box_node("Input Sentence", width=3.0)
    nodes["tokenizer"] = create_box_node("Tokenizer")
    nodes["embedding"] = create_box_node("Embedding")
    nodes["positional_encoding"] = create_box_node("Positional\nEncoding", height=0.9)
    nodes["encoder_block"] = create_box_node("Encoder Block\n(Self-Attention + FFN)", height=1.2)
    nodes["self_attention"] = create_box_node("Self-Attention", width=2.4)
    nodes["ffn"] = create_box_node("Feed-Forward\nNetwork", height=0.9)
    nodes["logits"] = create_box_node("Output\nLogits")
    nodes["softmax"] = create_box_node("Softmax\n+ Argmax")

    # 위치 배치
    for key, cfg in TRANSFORMER_LAYOUT_TEMPLATE.items():
        if key in nodes:
            nodes[key].move_to(cfg["pos"])

    return nodes


# === 5. CNN 전용 (간략) 레이아웃 템플릿 ===

CNN_LAYOUT_TEMPLATE: Dict[str, Dict] = {
    "input": {"shape": "box", "pos": LEFT * 5},
    "padded": {"shape": "box", "pos": LEFT * 3},
    "kernel": {"shape": "box", "pos": LEFT * 1 + UP * 1.5},
    "feature_map": {"shape": "box", "pos": RIGHT * 1},
    "relu": {"shape": "box", "pos": RIGHT * 3},
    "pool": {"shape": "box", "pos": RIGHT * 5},
}


def build_cnn_nodes() -> Dict[str, VGroup]:
    """CNN 플로우(입력→패딩→커널→feature map→ReLU→Pool)용 노드들."""
    nodes = {}
    nodes["input"] = create_box_node("Input\nImage", width=2.2)
    nodes["padded"] = create_box_node("Zero Pad", width=2.0)
    nodes["kernel"] = create_box_node("Conv\nKernel", width=1.8)
    nodes["feature_map"] = create_box_node("Feature Map", width=2.4)
    nodes["relu"] = create_box_node("ReLU", width=1.4)
    nodes["pool"] = create_box_node("Max Pool", width=1.6)

    for key, cfg in CNN_LAYOUT_TEMPLATE.items():
        if key in nodes:
            nodes[key].move_to(cfg["pos"])

    return nodes


# === 6. 오버플로우 대응: 자동 리스케일 ===

def autorescale_group(
    group: VGroup,
    max_width: float = 12.0,
    max_height: float = 6.5,
    margin: float = 0.5,
):
    """그룹이 화면 밖으로 나가지 않도록 자동 스케일/이동.

    - group.width, group.height를 확인해서 max_*보다 크면 비율로 축소.
    - 이후 화면 중앙 근처로 move_to.
    """
    # Manim의 기본 카메라 프레임 크기 (config.frame_width/height)
    fw = config.frame_width
    fh = config.frame_height

    limit_w = min(max_width, fw - 2 * margin)
    limit_h = min(max_height, fh - 2 * margin)

    scale_factor = 1.0
    if group.width > limit_w:
        scale_factor = min(scale_factor, limit_w / group.width)
    if group.height > limit_h:
        scale_factor = min(scale_factor, limit_h / group.height)

    if scale_factor < 1.0:
        group.scale(scale_factor)

    group.move_to(ORIGIN)
    return group


# === 7. 공통 화살표/엣지 유틸 ===

def connect_nodes(src: VGroup, dst: VGroup, buff: float = 0.2, color=GRAY) -> Arrow:
    """두 노드 중심을 기준으로 오른쪽→왼쪽 또는 아래→위 방향 화살표 생성."""
    start = src.get_right()
    end = dst.get_left()

    # 세로 방향 차이가 더 크면 위/아래 연결로 간주
    if abs(start[1] - end[1]) > abs(start[0] - end[0]):
        if src.get_center()[1] > dst.get_center()[1]:
            start = src.get_bottom()
            end = dst.get_top()
        else:
            start = src.get_top()
            end = dst.get_bottom()

    arrow = Arrow(start, end, buff=buff, stroke_color=color)
    return arrow


def fanout_arrows(src: VGroup, dst_list: List[VGroup], color=GRAY, buff: float = 0.2) -> VGroup:
    """하나의 노드에서 여러 노드로 나가는 얇은 화살표 묶음."""
    arrows = []
    for dst in dst_list:
        arrows.append(connect_nodes(src, dst, buff=buff, color=color))
    return VGroup(*arrows)


# === 8. Scene 헬퍼 믹스인 (선택적으로 상속해서 사용) ===

class LayoutMixin:
    """공통 레이아웃 유틸을 Scene과 함께 쓰기 위한 믹스인."""

    def add_with_autorescale(self, *mobjects):
        group = VGroup(*mobjects)
        autorescale_group(group)
        self.add(group)
        return group

    def add_edges_for_sequence(self, nodes: List[VGroup], color=GRAY, buff: float = 0.2) -> VGroup:
        arrows = []
        for a, b in zip(nodes, nodes[1:]):
            arrows.append(connect_nodes(a, b, buff=buff, color=color))
        edge_group = VGroup(*arrows)
        self.add(edge_group)
        return edge_group
