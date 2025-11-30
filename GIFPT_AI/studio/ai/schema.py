# app/schema.py
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
