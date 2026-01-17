# server/modules_person.py
"""
人物体征分析模块（严格 evidence gate + 三元证据字段）

人物体征估计规则：
- 身高：只能输出 "偏高/中等/偏矮/无法判断"
- 体型：只能输出 "偏瘦/匀称/偏壮/无法判断"
- 姿态：只能输出 "挺拔/放松/含胸/不确定"
- 性别：只能输出 "男性/女性/无法判断"

evidence 必须包含三要素：
- 参照物：画面中可用于参照的物体
- 全身：是否可见全身轮廓
- 角度影响：拍摄角度对判断的影响

如果 evidence 缺少任何一个要素，强制降级。
"""
from typing import Any, Dict, List, Optional, Tuple


# 人物体征 evidence 必须包含的三个关键字段
REQUIRED_EVIDENCE_KEYS = ["参照物", "全身", "角度影响"]

# 允许的输出值
VALID_HEIGHT = {"偏高", "中等", "偏矮", "无法判断"}
VALID_BODY_TYPE = {"偏瘦", "匀称", "偏壮", "无法判断"}
VALID_POSTURE = {"挺拔", "放松", "含胸", "不确定"}
VALID_GENDER = {"男性", "女性", "无法判断"}


def validate_person_evidence(evidence: Dict[str, str]) -> Tuple[bool, List[str]]:
    """
    验证人物体征 evidence 是否满足三要素要求
    
    Returns:
        (is_valid, missing_keys)
    """
    if not evidence:
        return False, REQUIRED_EVIDENCE_KEYS.copy()
    
    # 检查三个关键字段
    evidence_blob = " ".join(str(v) for v in evidence.values())
    missing = []
    
    for key in REQUIRED_EVIDENCE_KEYS:
        if key not in evidence_blob:
            # 检查是否有对应的字段
            has_field = False
            for k, v in evidence.items():
                if key in k or key in str(v):
                    has_field = True
                    break
            if not has_field:
                missing.append(key)
    
    return len(missing) == 0, missing


def _normalize_height(value: str) -> str:
    """规范化身高输出"""
    if not value:
        return "无法判断"
    value = str(value).strip()
    if value in VALID_HEIGHT:
        return value
    # 尝试模糊匹配
    if "高" in value and "偏" not in value:
        return "偏高"
    if "矮" in value:
        return "偏矮"
    if "中" in value:
        return "中等"
    return "无法判断"


def _normalize_body_type(value: str) -> str:
    """规范化体型输出"""
    if not value:
        return "无法判断"
    value = str(value).strip()
    if value in VALID_BODY_TYPE:
        return value
    # 尝试模糊匹配
    if "瘦" in value:
        return "偏瘦"
    if "壮" in value or "胖" in value:
        return "偏壮"
    if "匀" in value or "正常" in value:
        return "匀称"
    return "无法判断"


def _normalize_posture(value: str) -> str:
    """规范化姿态输出"""
    if not value:
        return "不确定"
    value = str(value).strip()
    if value in VALID_POSTURE:
        return value
    # 尝试模糊匹配
    if "挺" in value:
        return "挺拔"
    if "放松" in value or "松弛" in value:
        return "放松"
    if "含胸" in value or "驼背" in value:
        return "含胸"
    return "不确定"


def _normalize_gender(value: str) -> str:
    """规范化性别输出"""
    if not value:
        return "无法判断"
    value = str(value).strip()
    if value in VALID_GENDER:
        return value
    # 尝试模糊匹配
    if "男" in value:
        return "男性"
    if "女" in value:
        return "女性"
    return "无法判断"


def _validate_gender_evidence(gender_evidence: Dict[str, str]) -> Tuple[bool, str]:
    """
    验证性别判断的证据是否充分
    
    Returns:
        (is_valid, reason)
    """
    if not gender_evidence:
        return False, "缺少性别判断证据"
    
    appearance = gender_evidence.get("appearance", "")
    environment = gender_evidence.get("environment", "")
    consistency = gender_evidence.get("consistency", "")
    
    # 检查是否有有效线索
    has_appearance_clue = appearance and "未见" not in appearance and "无法" not in appearance
    has_env_clue = environment and "未见" not in environment and "无法" not in environment
    
    # 至少需要一个有效线索
    if not has_appearance_clue and not has_env_clue:
        return False, "外观线索和环境线索均不足"
    
    # 检查线索一致性
    if "矛盾" in consistency or "不一致" in consistency:
        return False, "多个线索指向不一致"
    
    return True, ""


def _build_evidence_from_context(
    det: Dict[str, Any],
    cred: Dict[str, Any],
    qwen_result: Dict[str, Any]
) -> Dict[str, str]:
    """
    从多个来源构建人物体征 evidence
    确保包含三要素：参照物、全身、角度影响
    """
    evidence = {}
    
    # 1. 参照物
    reference_objects = det.get("reference_objects", [])
    if reference_objects:
        obj_names = list(set([o["label"] for o in reference_objects[:5]]))
        evidence["reference"] = f"参照物：检测到 {', '.join(obj_names)}（来自{det.get('engine', 'unknown')}检测）"
    else:
        # 尝试从 Qwen 结果获取
        qwen_objects = qwen_result.get("objects", {}).get("detected", [])
        if qwen_objects:
            evidence["reference"] = f"参照物：Qwen 识别到 {', '.join(qwen_objects[:5])}"
        else:
            evidence["reference"] = "参照物：未检测到明显参照物（无法进行尺寸对比）"
    
    # 2. 全身可见性
    person_visibility = det.get("person_visibility", {})
    visibility = person_visibility.get("visibility", "不可见")
    detail = person_visibility.get("detail", "")
    evidence["body_visibility"] = f"全身：{visibility}（{detail}）" if detail else f"全身：{visibility}"
    
    # 从 Qwen 结果补充
    qwen_person = qwen_result.get("person", {})
    qwen_evidence = qwen_person.get("evidence", {})
    if qwen_evidence.get("body_visibility"):
        evidence["body_visibility"] = qwen_evidence["body_visibility"]
    
    # 3. 角度影响
    angle_impact = cred.get("angle_impact", {})
    evidence["angle_impact"] = angle_impact.get("evidence", "角度影响：未知（无法评估）")
    
    # 如果 Qwen 提供了更具体的角度判断，使用它
    if qwen_evidence.get("angle_impact"):
        evidence["angle_impact"] = qwen_evidence["angle_impact"]
    
    return evidence


def _force_add_missing_evidence(evidence: Dict[str, str], missing: List[str]) -> Dict[str, str]:
    """为缺失的 evidence 字段添加默认值"""
    result = dict(evidence)
    
    defaults = {
        "参照物": "参照物：未检测到（信息不足，无法进行身高/体型推断）",
        "全身": "全身：不可见或无法判断（信息不足）",
        "角度影响": "角度影响：未知（缺少焦距信息，无法评估透视影响）"
    }
    
    for key in missing:
        if key == "参照物":
            result["reference"] = defaults[key]
        elif key == "全身":
            result["body_visibility"] = defaults[key]
        elif key == "角度影响":
            result["angle_impact"] = defaults[key]
    
    return result


def person_module(
    det: Dict[str, Any],
    cred: Dict[str, Any],
    qwen_result: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    人物体征分析主入口
    
    严格执行 evidence gate：
    - 如果 evidence 缺少三要素中的任何一个
    - 身高/体型 强制输出 "无法判断"
    - 姿态 强制输出 "不确定"
    
    Args:
        det: 本地检测结果
        cred: 可信度分析结果
        qwen_result: Qwen VL 分析结果（可选）
    
    Returns:
        人物体征分析结果
    """
    qwen_result = qwen_result or {}
    
    # 检查是否检测到人物
    persons = det.get("persons", [])
    if not persons:
        return {
            "detected": False,
            "count": 0,
            "gender": "无法判断",
            "gender_evidence": {
                "appearance": "外观线索：N/A（未检测到人物）",
                "environment": "环境线索：N/A",
                "consistency": "线索一致性：N/A"
            },
            "height": "无法判断",
            "body_type": "无法判断",
            "posture": "不确定",
            "evidence": {
                "reference": "参照物：N/A（未检测到人物）",
                "body_visibility": "全身：不可见（未检测到人物）",
                "angle_impact": "角度影响：N/A（未检测到人物）"
            },
            "evidence_list": ["来自检测：当前画面未检测到人物"],
            "limitations": ["无人物，无法进行体征分析"],
            "confidence": "low"
        }
    
    # 构建 evidence
    evidence = _build_evidence_from_context(det, cred, qwen_result)
    
    # 验证 evidence 是否满足三要素
    is_valid, missing = validate_person_evidence(evidence)
    
    # 如果缺失，补充默认值
    if missing:
        evidence = _force_add_missing_evidence(evidence, missing)
    
    # 从 Qwen 结果获取分析
    qwen_person = qwen_result.get("person", {})
    
    # 性别判断（单独处理，不受体征 evidence gate 影响）
    gender_evidence = qwen_person.get("gender_evidence", {})
    gender_valid, gender_reason = _validate_gender_evidence(gender_evidence)
    
    if gender_valid:
        gender = _normalize_gender(qwen_person.get("gender", ""))
    else:
        gender = "无法判断"
        # 补充默认的 gender_evidence
        if not gender_evidence:
            gender_evidence = {
                "appearance": "外观线索：未提供有效线索",
                "environment": "环境线索：未提供有效线索",
                "consistency": f"线索一致性：{gender_reason}"
            }
    
    # 如果 evidence 不完整，强制降级（身高/体型/姿态）
    if not is_valid:
        height = "无法判断"
        body_type = "无法判断"
        posture = "不确定"
        confidence = "low"
        limitations = [
            f"evidence 缺少必要字段：{', '.join(missing)}",
            "因证据不足，身高/体型强制降级为'无法判断'，姿态降级为'不确定'"
        ]
    else:
        # evidence 完整，使用 Qwen 的分析结果（经过规范化）
        height = _normalize_height(qwen_person.get("height", ""))
        body_type = _normalize_body_type(qwen_person.get("body_type", ""))
        posture = _normalize_posture(qwen_person.get("posture", ""))
        confidence = qwen_person.get("confidence", "low")
        limitations = ["人物体征估计受拍摄角度、参照物等因素影响，仅供参考"]
        
        # 额外校验：如果参照物不明显，也应该更保守
        if "未检测到" in evidence.get("reference", "") or "无明显" in evidence.get("reference", ""):
            if height != "无法判断":
                height = "无法判断"
                limitations.append("参照物不明显，身高判断降级")
            if body_type != "无法判断":
                body_type = "无法判断"
                limitations.append("参照物不明显，体型判断降级")
    
    # 构建 evidence_list（用于前端展示）
    evidence_list = [
        evidence.get("reference", ""),
        evidence.get("body_visibility", ""),
        evidence.get("angle_impact", "")
    ]
    evidence_list = [e for e in evidence_list if e]  # 过滤空值
    
    return {
        "detected": True,
        "count": len(persons),
        "gender": gender,
        "gender_evidence": gender_evidence,
        "height": height,
        "body_type": body_type,
        "posture": posture,
        "evidence": evidence,
        "evidence_list": evidence_list,
        "limitations": limitations,
        "confidence": confidence,
        "_qwen_raw": qwen_person if qwen_person else None
    }
