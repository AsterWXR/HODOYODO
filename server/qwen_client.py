# server/qwen_client.py
"""
Gemini 3 多模态模型客户端（通过 OpenRouter API）
"""
import os
import base64
import json
import requests
from typing import Any, Dict, Optional

DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3-pro-preview")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def _image_to_base64_url(image_bytes: bytes, mime: str = "image/jpeg") -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"


async def analyze_with_qwen(
    image_bytes: bytes,
    mime: str = "image/jpeg",
    model: str = DEFAULT_MODEL,
    extra_context: Optional[Dict[str, Any]] = None,
    target_gender: str = "boyfriend"
) -> Dict[str, Any]:
    """使用 Gemini 3 分析图片，输出完整分析结果"""
    
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        return {"_success": False, "_error": "缺少 OPENROUTER_API_KEY", "_model": model}
    
    target_word = "男朋友" if target_gender == "boyfriend" else "女朋友"
    opposite = "女性用品" if target_gender == "boyfriend" else "男性用品"

    # 完整 prompt，输出详细分析结果
    system_prompt = f"""你是一个专业的照片分析AI。请分析「{target_word}」发的照片，特别关注{opposite}相关的线索。

**重要：你必须严格按照以下JSON格式输出，不能省略任何字段，所有字段都必须有值。**

输出完整JSON：
```json
{{
  "person": {{
    "detected": bool,
    "count": int,
    "height": "偏高/中等/偏矮/无法判断",
    "body_type": "偏瘦/匀称/偏壮/无法判断",
    "posture": "挺拔/放松/含胸/不确定",
    "gender": "男性/女性/无法判断",
    "gender_evidence": {{
      "appearance": "外观线索描述",
      "environment": "环境线索描述",
      "consistency": "线索一致性说明"
    }},
    "evidence": {{
      "reference": "参照物描述",
      "body_visibility": "全身可见性描述",
      "angle_impact": "角度影响说明"
    }},
    "partial_features": {{
      "hand": "手部特征",
      "arm": "手臂特征",
      "face": "脸部特征",
      "neck_shoulder": "颈肩特征",
      "body": "身体特征",
      "body_type_clue": "体型综合判断"
    }},
    "confidence": "high/medium/low"
  }},
  "web_image_check": {{
    "risk_level": "high/medium/low",
    "watermark": "水印描述或null",
    "screenshot": "截图痕迹或null",
    "professional": "专业摄影特征或null"
  }},
  "scene": {{
    "location": "室内/室外",
    "desc": "详细环境描述"
  }},
  "lifestyle": {{
    "level": "高/中/大众/无法判断",
    "brands": ["品牌列表"]
  }},
  "room_analysis": {{
    "people": "1/2/无法判断",
    "relation": "独居/情侣/无法判断",
    "evidence": "详细依据"
  }},
  "objects": ["检测到的物体列表"],
  "details": {{
    "text": ["识别到的文字列表"],
    "special": ["特殊元素列表"]
  }},
  "intention": "照片用途详细说明",
  "girlfriend_comments": ["可疑点吐槽列表"]
}}
```

规则：
1. 水印/截图/专业摄影是网图高风险线索
2. 看到人体任何部位就给体型判断，默认匀称
3. girlfriend_comments用口语化吐槽，如"宝这图有点意思"
4. 无依据输出"无法判断"
5. **必须输出完整的JSON，包含所有字段，不能省略任何字段**
6. **所有字段都必须有值，不能为null或空**
7. **只输出JSON，不要任何其他文字、解释或说明**
8. **确保JSON格式正确，可以直接被解析**"""

    image_url = _image_to_base64_url(image_bytes, mime)
    user_text = "请仔细分析这张照片，严格按照上述JSON格式输出完整结果。必须包含所有字段，不能省略。"
    if extra_context:
        user_text += f"\n辅助信息：{json.dumps(extra_context, ensure_ascii=False)}"

    # OpenRouter/Gemini 使用 OpenAI 兼容格式
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": [
            {"type": "text", "text": user_text},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]}
    ]

    try:
        resp = requests.post(
            OPENROUTER_API_URL,
            headers={
                "Authorization": f"Bearer {openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",  # OpenRouter 推荐
                "X-Title": "Watcha Security"  # OpenRouter 推荐（使用英文避免编码问题）
            },
            json={"model": model, "messages": messages, "temperature": 0.0},
            timeout=120
        )
        
        if not resp.ok:
            return {"_success": False, "_error": f"HTTP {resp.status_code}", "_raw_response": resp.text[:500], "_model": model}

        data = resp.json()
        content = ""
        try:
            content = data.get("choices", [])[0].get("message", {}).get("content", "")
        except:
            pass

        if not content:
            return {"_success": False, "_error": "empty response", "_raw_response": resp.text[:500], "_model": model}

        # 去除代码块包裹，支持多种格式
        import re
        # 尝试提取代码块中的 JSON
        m = re.search(r"```(?:json)?\s*(.*?)```", content, re.S)
        if m:
            content = m.group(1).strip()
        else:
            # 如果没有代码块，尝试直接提取 JSON 对象
            # 查找第一个 { 到最后一个 } 之间的内容
            first_brace = content.find('{')
            last_brace = content.rfind('}')
            if first_brace >= 0 and last_brace > first_brace:
                content = content[first_brace:last_brace+1].strip()

        # 解析 JSON
        try:
            parsed = json.loads(content)
            
            # 转换模型输出格式到完整格式（兼容完整和精简格式）
            result = _expand_compact_result(parsed)
            result["_success"] = True
            result["_model"] = model
            result["_raw_response"] = content
            # 添加调试信息：检查关键字段是否存在
            missing_fields = []
            if not result.get("person"):
                missing_fields.append("person")
            if not result.get("web_image_check"):
                missing_fields.append("web_image_check")
            if not result.get("scene"):
                missing_fields.append("scene")
            if not result.get("lifestyle"):
                missing_fields.append("lifestyle")
            if missing_fields:
                result["_missing_fields"] = missing_fields
            return result
        except json.JSONDecodeError as e:
            # 尝试修复截断的 JSON
            try:
                last_brace = content.rfind('}')
                if last_brace > 0:
                    partial = json.loads(content[:last_brace+1])
                    result = _expand_compact_result(partial)
                    result["_success"] = True
                    result["_model"] = model
                    result["_partial"] = True
                    result["_raw_response"] = content[:500]
                    return result
            except Exception as e2:
                pass
            # 返回错误信息，包含原始响应以便调试
            return {
                "_success": False, 
                "_error": f"JSON parse error: {e}", 
                "_raw_response": content[:1000],  # 增加长度以便调试
                "_model": model
            }

    except Exception as e:
        return {"_success": False, "_error": str(e), "_model": model}


def _expand_compact_result(compact: Dict[str, Any]) -> Dict[str, Any]:
    """将模型输出格式转换为完整格式，兼容 pipeline.py"""
    
    # person 转换
    person = compact.get("person", {})
    expanded_person = {
        "detected": person.get("detected", False),
        "count": person.get("count", 0),
        "height": person.get("height", "无法判断"),
        "body_type": person.get("body_type", "无法判断"),
        "posture": person.get("posture", "不确定"),
        "gender": person.get("gender", "无法判断"),
        "gender_evidence": person.get("gender_evidence", {
            "appearance": "无",
            "environment": "无",
            "consistency": "无"
        }),
        "evidence": person.get("evidence", {}) if isinstance(person.get("evidence"), dict) else {
            "reference": "无",
            "body_visibility": "无",
            "angle_impact": "无"
        },
        "partial_features": person.get("partial_features", {}),
        "confidence": person.get("confidence", "low")
    }
    
    # web_image_check 转换
    web = compact.get("web_image_check", {})
    expanded_web = {
        "risk_level": web.get("risk_level", "无法判断"),
        "is_likely_web_image": web.get("risk_level") == "high",
        "watermark": {
            "detected": bool(web.get("watermark")),
            "platform": web.get("watermark") if web.get("watermark") else None,
            "location": None,
            "evidence": web.get("watermark", "")
        },
        "screenshot_traces": {
            "detected": bool(web.get("screenshot")),
            "type": web.get("screenshot") if web.get("screenshot") else "无",
            "evidence": web.get("screenshot", "")
        },
        "professional_photo": {
            "detected": bool(web.get("professional")),
            "features": [web.get("professional")] if web.get("professional") else [],
            "evidence": web.get("professional", "")
        },
        "image_quality_issues": {"compression_artifacts": False, "resolution_mismatch": False, "aspect_ratio_abnormal": False, "evidence": ""},
        "influencer_style": {"detected": False, "features": [], "evidence": ""},
        "temporal_inconsistency": {"detected": False, "evidence": ""},
        "conclusion": f"风险等级: {web.get('risk_level', '无法判断')}",
        "recommendation": "建议使用百度识图验证" if web.get("risk_level") == "high" else None
    }
    
    # scene 转换
    scene = compact.get("scene", {})
    expanded_scene = {
        "location_type": scene.get("location", "无法判断"),
        "environment": scene.get("desc", ""),
        "evidence": [scene.get("desc", "")] if scene.get("desc") else [],
        "confidence": "medium"
    }
    
    # lifestyle 转换
    lifestyle = compact.get("lifestyle", {})
    brands_raw = lifestyle.get("brands", [])
    # 确保 brands 是列表
    if not isinstance(brands_raw, list):
        brands_raw = []
    
    expanded_lifestyle = {
        "claim": f"消费水平: {lifestyle.get('level', '无法判断')}",
        "consumption_level": lifestyle.get("level", "无法判断"),
        "accommodation_level": lifestyle.get("accommodation_level", "无法判断"),
        "brands_detected": {
            "clothing": brands_raw,  # 暂时全部放在 clothing，后续可以分类
            "accessories": [],
            "electronics": [],
            "skincare": [],
            "other": []
        },
        "evidence": [],
        "limitations": [],
        "confidence": "low"
    }
    
    # room_analysis 转换
    room = compact.get("room_analysis", {})
    room_evidence = room.get("evidence", "")
    # 处理 evidence 可能是字符串或列表的情况
    if isinstance(room_evidence, str):
        room_evidence_list = [room_evidence] if room_evidence else []
    elif isinstance(room_evidence, list):
        room_evidence_list = room_evidence
    else:
        room_evidence_list = []
    
    expanded_room = {
        "inferred_people_count": room.get("people", "无法判断"),
        "relationship_hint": room.get("relation", "无法判断"),
        "evidence": room_evidence_list,
        "clues": {},
        "limitations": ["环境推断存在不确定性"],
        "confidence": "low"
    }
    
    # objects 转换
    objects_raw = compact.get("objects", [])
    # 处理 objects 可能是字符串或其他格式的情况
    if isinstance(objects_raw, list):
        objects_list = objects_raw
    elif isinstance(objects_raw, str):
        objects_list = [objects_raw] if objects_raw else []
    else:
        objects_list = []
    
    expanded_objects = {
        "detected": objects_list,
        "brands": [],
        "evidence": []
    }
    
    # details 转换
    details = compact.get("details", {})
    # 处理 details 可能是字符串的情况（向后兼容）
    if isinstance(details, str):
        details = {}
    text_list = details.get("text", [])
    if not isinstance(text_list, list):
        text_list = []
    special_list = details.get("special", [])
    if not isinstance(special_list, list):
        special_list = []
    
    expanded_details = {
        "text_detected": text_list,
        "text_type": "混合" if text_list else "无文字",
        "text_source": "",
        "special_elements": special_list,
        "evidence": []
    }
    
    # intention 转换
    intention = compact.get("intention", "")
    if isinstance(intention, dict):
        # 如果 intention 是字典，提取 claim
        intention_claim = intention.get("claim", intention.get("intention", "无法判断"))
    else:
        intention_claim = intention if isinstance(intention, str) else "无法判断"
    
    expanded_intention = {
        "claim": intention_claim,
        "evidence": [],
        "confidence": "low"
    }
    
    return {
        "person": expanded_person,
        "web_image_check": expanded_web,
        "scene": expanded_scene,
        "lifestyle": expanded_lifestyle,
        "room_analysis": expanded_room,
        "objects": expanded_objects,
        "details": expanded_details,
        "intention": expanded_intention,
        "girlfriend_comments": compact.get("girlfriend_comments", [])
    }
