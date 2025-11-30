# ai/schema.py
from jsonschema import Draft7Validator
from typing import Dict, Any, List

JSON_IR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["components", "events"],
    "properties": {
        "components": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "string"},
                    # 선택: 정적 레이아웃/메타데이터
                    "pos": {
                        "type": "array",
                        "minItems": 3,
                        "maxItems": 3,
                        "items": {"type": "number"}
                    },
                    "label": {"type": "string"},
                    "style": {"type": "object"}
                }
            }
        },
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["t", "op"],
                "properties": {
                    "t": {"type": "number"},
                    "op": {"type": "string"},
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "target": {"type": "string"},
                    "item": {"type": "string"},
                    "data": {}
                }
            }
        },
        "metadata": {"type": "object"}
    },
    "additionalProperties": True
}

def schema_errors(doc: Dict[str, Any]) -> List[str]:
    v = Draft7Validator(JSON_IR_SCHEMA)
    return [f"{e.message} at {list(e.absolute_path)}" for e in v.iter_errors(doc)]

def invariants_errors(doc: Dict[str, Any]) -> List[str]:
    """
    도메인 불변성 체크 예시:
      - events.t 오름차순
      - from/to/target 참조는 components.id 중 하나여야 함
    필요 시 알고리즘별 규칙을 더 추가하세요.
    """
    errors: List[str] = []
    comp_ids = {c["id"] for c in doc.get("components", []) if "id" in c}
    evts = doc.get("events", [])

    # 시간 오름차순
    if any(evts[i]["t"] > evts[i+1]["t"] for i in range(len(evts)-1)):
        errors.append("events.t must be non-decreasing order")

    # from/to/target 참조 유효성
    for i, e in enumerate(evts):
        for k in ("from", "to", "target"):
            if k in e and e[k] not in comp_ids:
                errors.append(f"event[{i}] references undefined '{k}': {e[k]}")

    return errors

# === seq_attention (Transformer Attention 패턴) IR 스키마 ===

ATTENTION_IR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["pattern_type", "tokens", "weights", "query_index"],
    "properties": {
        "pattern_type": {
            "type": "string",
            "const": "seq_attention",
        },
        "raw_text": {                     
            "type": "string",
        },
        "tokens": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "weights": {
            "type": "array",
            "minItems": 1,
            "items": {
                "oneOf": [
                    # 1D: [w0, w1, ..., w_{N-1}]
                    {"type": "number"},
                    # 2D: [[...], [...], ...] 도 나중에 쓸 수 있게 남겨둠
                    {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "number"},
                    },
                ]
            },
        },
        "query_index": {
            "type": "integer",
            "minimum": 0,
        },
        "next_token": {                 
            "type": "object",
            "required": ["candidates", "probs"],
            "properties": {
                "candidates": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
                "probs": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 1,
                },
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,     
}


ATTENTION_IR_VALIDATOR = Draft7Validator(ATTENTION_IR_SCHEMA)

# ============ GRID IR Schema (CNN, Heatmap) ============
GRID_IR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["pattern", "bounds", "layout", "components", "actions"],
    "properties": {
        "pattern": {
            "type": "string",
            "const": "grid",
        },
        
        "bounds": {
            "type": "object",
            "required": ["xmin", "xmax", "ymin", "ymax"],
            "properties": {
                "xmin": {"type": "number"},
                "xmax": {"type": "number"},
                "ymin": {"type": "number"},
                "ymax": {"type": "number"}
            },
            "additionalProperties": False,
        },
        
        "layout": {
            "type": "object",
            "required": ["n_rows", "n_cols", "cell_size"],
            "properties": {
                "n_rows": {"type": "integer", "minimum": 1},
                "n_cols": {"type": "integer", "minimum": 1},
                "cell_size": {"type": "number", "minimum": 0.1, "maximum": 1.0},
                "cell_gap": {"type": "number", "minimum": 0, "maximum": 0.5},
                "start_x": {"type": "number"},
                "start_y": {"type": "number"}
            },
            "additionalProperties": False,
        },
        
        "components": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "type", "grid_pos"],
                "properties": {
                    "id": {"type": "string"},
                    "type": {"type": "string", "enum": ["cell", "label"]},
                    "grid_pos": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 2,
                        "items": {"type": "integer"}
                    },
                    "value": {"type": ["string", "number"]},
                    "color": {"type": "string"}
                },
                "additionalProperties": True,
            }
        },
        
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["t", "type"],
                "properties": {
                    "t": {"type": "number", "minimum": 0},
                    "type": {"type": "string"},  # 유연하게: enum 제거
                    "target": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}}
                        ]
                    },
                    "color": {"type": "string"},
                    "value": {"type": ["string", "number"]},
                    "duration": {"type": "number", "minimum": 0.1}
                },
                "additionalProperties": True,
            }
        },
        
        "metadata": {"type": "object"}
    },
    "additionalProperties": False,
}

GRID_IR_VALIDATOR = Draft7Validator(GRID_IR_SCHEMA)


# ============ SEQUENCE IR Schema (Sorting, Timeline) ============
SEQUENCE_IR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["pattern", "bounds", "layout", "components", "actions"],
    "properties": {
        "pattern": {
            "type": "string",
            "const": "sequence",
        },
        
        "bounds": {
            "type": "object",
            "required": ["xmin", "xmax", "ymin", "ymax"],
            "properties": {
                "xmin": {"type": "number"},
                "xmax": {"type": "number"},
                "ymin": {"type": "number"},
                "ymax": {"type": "number"}
            },
            "additionalProperties": False,
        },
        
        "layout": {
            "type": "object",
            "required": ["n_items", "item_size"],
            "properties": {
                "n_items": {"type": "integer", "minimum": 1},
                "item_size": {"type": "number", "minimum": 0.3, "maximum": 1.0},
                "item_gap": {"type": "number", "minimum": 0.1, "maximum": 0.5},
                "baseline_y": {"type": "number"},
                "start_x": {"type": "number"}
            },
            "additionalProperties": False,
        },
        
        "components": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "type", "seq_pos"],
                "properties": {
                    "id": {"type": "string"},
                    "type": {"type": "string", "enum": ["circle", "square", "label"]},
                    "seq_pos": {"type": "integer", "minimum": 0},
                    "value": {"type": ["string", "number"]},
                    "radius": {"type": "number", "minimum": 0.2},
                    "color": {"type": "string"}
                },
                "additionalProperties": True,
            }
        },
        
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["t", "type"],
                "properties": {
                    "t": {"type": "number", "minimum": 0},
                    "type": {"type": "string"},  # 유연하게: enum 제거
                    "from": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}}
                        ]
                    },
                    "to": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}}
                        ]
                    },
                    "target": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}}
                        ]
                    },
                    "duration": {"type": "number", "minimum": 0.1},
                    "color": {"type": "string"}
                },
                "additionalProperties": True,
            }
        },
        
        "metadata": {"type": "object"}
    },
    "additionalProperties": False,
}

SEQUENCE_IR_VALIDATOR = Draft7Validator(SEQUENCE_IR_SCHEMA)


def validate_attention_ir(doc: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    # 1) jsonschema 기반 기본 검증
    for err in ATTENTION_IR_VALIDATOR.iter_errors(doc):
        errors.append(err.message)

    tokens = doc.get("tokens", [])
    weights = doc.get("weights", [])

    # 2) weights 형태 검사
    if isinstance(weights, list) and weights:
        first = weights[0]

        # --- case 1: 2D matrix [[...], [...], ...] ---
        if isinstance(first, list):
            if len(weights) != len(tokens):
                errors.append("len(weights) must equal len(tokens) for 2D weights")

            row_len = len(first)
            if any(len(row) != row_len for row in weights):
                errors.append("all rows in weights must have the same length")

        # --- case 2: 1D row [w_0, w_1, ..., w_n-1] ---
        else:
            if len(weights) != len(tokens):
                errors.append("len(weights) must equal len(tokens) for 1D weights")

    # 3) query_index 범위 체크
    qi = doc.get("query_index")
    if isinstance(qi, int) and not (0 <= qi < len(tokens)):
        errors.append("query_index out of range")

    # 4) next_token (선택) 검증
    nt = doc.get("next_token")
    if nt is not None:
        cands = nt.get("candidates")
        probs = nt.get("probs")
        if not isinstance(cands, list) or not isinstance(probs, list):
            errors.append("next_token.candidates and probs must be lists")
        elif len(cands) != len(probs):
            errors.append("next_token.candidates and probs must have the same length")

    return errors


# ============ GRID IR 검증 함수 ============
VALID_COLORS = {
    "WHITE", "BLACK", "BLUE", "BLUE_B", "BLUE_D",
    "GREEN", "RED", "YELLOW", "YELLOW_B", "GRAY", "GRAY_B", "LIGHT_BLUE"
}


def validate_grid_ir(ir: Dict[str, Any]) -> List[str]:
    """
    GRID IR 검증:
    1. 기본 스키마 검증 (필수 필드만)
    2. 심각한 구조적 오류만 체크
    
    Note: 
    - grid_pos 범위 체크 제거 (LLM의 창의성 허용, ensure_on_screen이 처리)
    - 색상 체크 제거 (Manim이 처리)
    - 레이아웃 계산 체크 제거 (LLM과 ensure_on_screen이 처리)
    """
    errors: List[str] = []
    
    # 1) 스키마 기본 검증 (JSON 구조만)
    for err in GRID_IR_VALIDATOR.iter_errors(ir):
        # 필수 필드 누락만 에러
        if "required" in err.message.lower() or "type" in err.message.lower():
            errors.append(f"Schema: {err.message}")
    
    if errors:
        return errors  # 스키마 오류가 있으면 나머지 검증 불가능
    
    # 2) 심각한 구조적 오류만 체크
    components = ir.get("components", [])
    actions = ir.get("actions", [])
    
    # grid_pos 형식만 체크 (범위는 체크 안함!)
    for comp in components:
        grid_pos = comp.get("grid_pos", [])
        if grid_pos and len(grid_pos) != 2:
            errors.append(f"Component {comp['id']}: grid_pos must be [row, col], got {grid_pos}")
    
    # action 순서만 체크 (t 오름차순)
    times = [a.get("t", 0) for a in actions]
    if times and times != sorted(times):
        errors.append("Actions must be in non-decreasing order of time (t)")
    
    return errors


def validate_sequence_ir(ir: Dict[str, Any]) -> List[str]:
    """
    SEQUENCE IR 검증: 심각한 구조적 오류만 체크
    
    Note:
    - seq_pos 범위 체크 제거 (LLM 창의성 허용)
    - 색상 체크 제거 (Manim이 처리)
    - from/to 참조 검증 제거 (Manim이 처리)
    """
    errors: List[str] = []
    
    # 1) 스키마 기본 검증 (필수 필드만)
    for err in SEQUENCE_IR_VALIDATOR.iter_errors(ir):
        if "required" in err.message.lower() or "type" in err.message.lower():
            errors.append(f"Schema: {err.message}")
    
    if errors:
        return errors
    
    # 2) action 순서만 체크
    actions = ir.get("actions", [])
    times = [a.get("t", 0) for a in actions]
    if times and times != sorted(times):
        errors.append("Actions must be in non-decreasing order of time (t)")
    
    return errors


# === FLOW IR 스키마 (파이프라인, 데이터플로우 패턴) ===

FLOW_IR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["pattern", "bounds", "layout", "components", "actions"],
    "properties": {
        "pattern": {"type": "string", "enum": ["flow"]},
        "bounds": {
            "type": "object",
            "properties": {
                "xmin": {"type": "number"},
                "xmax": {"type": "number"},
                "ymin": {"type": "number"},
                "ymax": {"type": "number"},
            },
            "additionalProperties": False
        },
        "layout": {
            "oneOf": [
                # Dict format (preferred)
                {
                    "type": "object",
                    "properties": {
                        "stage_width": {"type": "number", "minimum": 0.5, "maximum": 2.0},
                        "stage_height": {"type": "number", "minimum": 0.5, "maximum": 2.0},
                        "spacing": {"type": "number", "minimum": 0.1, "maximum": 1.0},
                        "start_x": {"type": "number"},
                        "start_y": {"type": "number"},
                    },
                    "additionalProperties": False
                },
                # List format (fallback, treated as empty dict)
                {"type": "array"}
            ]
        },
        "components": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "string"},
                    "type": {"type": "string", "enum": ["stage", "block", "connector"]},
                    "label": {"type": "string"},
                    "color": {"type": "string"},
                    "position": {
                        "type": "array",
                        "minItems": 3,
                        "maxItems": 3,
                        "items": {"type": "number"}
                    },
                },
                "additionalProperties": True
            }
        },
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["t", "type"],
                "properties": {
                    "t": {"type": "number", "minimum": 0},
                    "type": {"type": "string"},  # 유연하게: enum 제거
                    "target": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}}
                        ]
                    },
                    "color": {"type": "string"},
                    "duration": {"type": "number", "minimum": 0},
                },
                "additionalProperties": True
            }
        },
        "metadata": {"type": "object", "additionalProperties": True}
    },
    "additionalProperties": True
}

FLOW_IR_VALIDATOR = Draft7Validator(FLOW_IR_SCHEMA)


def validate_flow_ir(ir: Dict[str, Any]) -> List[str]:
    """
    FLOW IR 검증: 심각한 구조적 오류만 체크
    
    Note:
    - bounds, layout 계산 체크 제거 (ensure_on_screen이 처리)
    - 색상 체크 제거 (Manim이 처리)
    - 참조 검증 제거 (Manim이 처리)
    """
    errors: List[str] = []
    
    # 1) 스키마 기본 검증 (필수 필드만)
    for err in FLOW_IR_VALIDATOR.iter_errors(ir):
        if "required" in err.message.lower() or "type" in err.message.lower():
            errors.append(f"Schema: {err.message}")
    
    if errors:
        return errors
    
    # 2) action 순서만 체크
    actions = ir.get("actions", [])
    times = [a.get("t", 0) for a in actions]
    if times and times != sorted(times):
        errors.append("Actions must be in non-decreasing order of time (t)")
    
    return errors


# ============ HASH_TABLE_IR_SCHEMA ============

HASH_TABLE_IR_SCHEMA = {
    "type": "object",
    "required": ["pattern", "bounds", "layout", "components", "actions"],
    "properties": {
        "pattern": {"type": "string"},
        "bounds": {"type": "object"},
        "layout": {"type": "object"},
        "components": {"type": "array"},
        "actions": {"type": "array"},
        "metadata": {"type": "object"}
    }
}

HASH_TABLE_IR_VALIDATOR = Draft7Validator(HASH_TABLE_IR_SCHEMA)


def validate_hash_table_ir(ir: Dict[str, Any]) -> List[str]:
    """Hash table IR validation."""
    errors: List[str] = []
    for err in HASH_TABLE_IR_VALIDATOR.iter_errors(ir):
        errors.append(f"Schema: {err.message}")
    return errors


# ============ GRAPH_IR_SCHEMA (Graph, Tree 패턴) ============

GRAPH_IR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["pattern", "nodes", "edges", "actions"],
    "properties": {
        "pattern": {
            "type": "string",
            "const": "graph",
        },
        
        "nodes": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "label"],
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "value": {"type": ["string", "number", "null"]},
                    "color": {"type": "string"},
                    "position": {
                        "type": "array",
                        "minItems": 3,
                        "maxItems": 3,
                        "items": {"type": "number"},
                        "description": "[x, y, z] position (z is usually 0)"
                    }
                },
                "additionalProperties": True,
            }
        },
        
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["from", "to"],
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "weight": {"type": ["number", "string", "null"]},
                    "label": {"type": ["string", "null"]},
                    "directed": {"type": "boolean"},
                    "color": {"type": "string"}
                },
                "additionalProperties": True,
            }
        },
        
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["t", "type"],
                "properties": {
                    "t": {"type": "number", "minimum": 0},
                    "type": {"type": "string"},  # 유연하게: enum 제거
                    "target": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}}
                        ]
                    },
                    "from": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}}
                        ]
                    },
                    "to": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}}
                        ]
                    },
                    "color": {"type": "string"},
                    "value": {"type": ["string", "number"]},
                    "duration": {"type": "number", "minimum": 0}
                },
                "additionalProperties": True,
            }
        },
        
        "layout": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["circle", "tree", "grid", "custom"]},
                "radius": {"type": "number"},
                "node_radius": {"type": "number"},
                "edge_thickness": {"type": "number"}
            },
            "additionalProperties": True
        },
        
        "metadata": {"type": "object", "additionalProperties": True}
    },
    "additionalProperties": True,
}

GRAPH_IR_VALIDATOR = Draft7Validator(GRAPH_IR_SCHEMA)


def validate_graph_ir(ir: Dict[str, Any]) -> List[str]:
    """
    GRAPH IR 검증: 심각한 구조적 오류만 체크
    
    Note:
    - 노드/엣지 참조 검증 제거 (Manim이 처리)
    - 색상 체크 제거 (Manim이 처리)
    - position 차원 검증만 유지
    """
    errors: List[str] = []
    
    # 1) 스키마 기본 검증 (필수 필드만)
    for err in GRAPH_IR_VALIDATOR.iter_errors(ir):
        if "required" in err.message.lower() or "type" in err.message.lower():
            errors.append(f"Schema: {err.message}")
    
    if errors:
        return errors
    
    nodes = ir.get("nodes", [])
    
    # 2) position 차원 검증 (Manim은 3D 좌표 필요)
    for node in nodes:
        pos = node.get("position")
        if pos and len(pos) != 3:
            errors.append(f"Node {node['id']}: position must be [x, y, z], got {pos}")
    
    # 3) action 순서만 체크
    actions = ir.get("actions", [])
    times = [a.get("t", 0) for a in actions]
    if times and times != sorted(times):
        errors.append("Actions must be in non-decreasing order of time (t)")
    
    return errors