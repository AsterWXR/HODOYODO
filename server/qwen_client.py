# server/qwen_client.py
"""
Qwen VL 多模态模型客户端
使用通义千问视觉语言模型进行图像分析
"""
import os
import base64
import json
from typing import Any, Dict, Optional
import dashscope
from dashscope import MultiModalConversation
from dashscope.api_entities.dashscope_response import Role

# 从环境变量读取 API Key，也可以直接设置
# export DASHSCOPE_API_KEY="your-api-key"
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY", "sk-8d685168110942009978c8f86c700bbf")

# 默认模型：qwen-vl-plus（性价比高）或 qwen-vl-max（效果最好）
DEFAULT_MODEL = "qwen-vl-max"


def _image_to_base64(image_bytes: bytes, mime: str = "image/jpeg") -> str:
    """将图片字节转为 base64 data URL"""
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"


async def analyze_with_qwen(
    image_bytes: bytes,
    mime: str = "image/jpeg",
    model: str = DEFAULT_MODEL,
    extra_context: Optional[Dict[str, Any]] = None,
    target_gender: str = "boyfriend"
) -> Dict[str, Any]:
    """
    使用 Qwen VL 多模态模型分析图片
    
    Args:
        image_bytes: 图片二进制数据
        mime: 图片MIME类型
        model: 使用的模型名称
        extra_context: 额外上下文信息（如本地检测结果）
        target_gender: 分析对象性别 ('boyfriend' 或 'girlfriend')
    
    Returns:
        分析结果字典
    """
    
    # 根据分析对象调整口语化输出风格
    if target_gender == "boyfriend":
        target_word = "男朋友"
        opposite_items = "女性用品（化妆品、护肤品、女性饰品、女鞋、女性内衣等）"
        suspect_hint = "这个情况有点微妙啊"
    else:
        target_word = "女朋友"
        opposite_items = "男性用品（剃须刀、男士护肤品、领带、男鞋、男性衣物等）"
        suspect_hint = "这个情况有点微妙啊"

    # 构建分析提示词（严格约束输出格式和 evidence 要求）
    system_prompt = f"""你是一个专业的照片分析专家，有过硬的先力学和痕迹学功底，负责帮助用户分析网恋场景中的照片真实性和人物特征，提供详细且准确的分析结果。

【当前分析对象】
用户正在分析「{target_word}」发送的照片，请重点关注是否有{opposite_items}出现。

【核心原则】
1. 每条结论都必须有明确的 evidence（画面依据），无依据则输出"无法判断"
2. 保持客观保守，不做过度推断
3. 所有结论必须可追溯到画面中的具体元素

【口语化总结风格要求】
girlfriend_comments 字段要用朋友吐槽的语气，像在帮朋友分析{target_word}发的照片，特点：
- 语气口语化、调侃，像聊天一样
- 直接指出可疑点，比如"宝两个人的，床头柜的东西应该只在一边才对"
- 根据画面实际内容分析，不要套用固定模板，每张照片都要量身定制
- 可以用网络用语，比如"宝""朋友""这个有点意思"
- 每条评论要基于画面中实际看到的内容，不要编造
- 重点关注：物品数量异常、{opposite_items}、反光中的人影、物品摆放不符合一个人使用的特征等
- 【禁止】不要使用任何脏话、粗口或不文明用语
- 【禁止】不要死扣"护手霜""小镜子"等固定物品，要根据实际画面内容分析
- 如果画面中没有可疑点，可以输出空数组[]或正面评价

【人物体征估计规则】（必须严格遵守）
- 身高：只能输出 "偏高/中等/偏矮/无法判断"
- 体型：只能输出 "偏瘦/匀称/偏壮/无法判断"
- 姿态：只能输出 "挚拔/放松/含胸/不确定"
- 性别：只能输出 "男性/女性/无法判断"

【局部特征判断体态规则】（即使只看到部分身体也可判断）
1. 手部特征（重要线索）：
   - 手指粗细：手指纤细修长倾向偏瘦，手指短粗有肉感倾向偏壮
   - 手腕粗细：手腕纤细可见骨骼倾向偏瘦，手腕圆润有肉感倾向偏壮
   - 手背肉感：手背平坦青筋可见倾向偏瘦，手背圆润有肉倾向偏壮
   - 指节特征：指节明显倾向偏瘦，指节不明显有肉感倾向偏壮

2. 手臂特征：
   - 手臂线条：手臂纤细线条分明倾向偏瘦，手臂圆润有肉感倾向偏壮
   - 手臂肌肉：背阴肌明显可能偏壮/健身，手臂松弛可能偏瘦

3. 脸部特征：
   - 脸型：脸部瘦削颧骨明显倾向偏瘦，脸部圆润有肉感倾向偏壮
   - 下巴线条：下巴尖锐线条分明倾向偏瘦，双下巴或下巴圆润倾向偏壮
   - 脸部轮廓：轮廓分明倾向偏瘦，轮廓柔和倾向偏壮

4. 颈部/肩部特征：
   - 颈部：颈部修长锁骨明显倾向偏瘦，颈部短粗倾向偏壮
   - 肩部：肩部线条分明倾向偏瘦，肩部圆润有肉感倾向偏壮

5. 判断原则：
   - 多个局部特征一致时可提高置信度
   - 仅有单一局部特征时置信度为 low
   - 特征矛盾或不清晰时输出"无法判断"

【性别判断规则】（结合外观特征和环境习惯综合判断）
1. 直接外观线索（权重高）：
   - 面部特征：胡须、喉结、妆容等
   - 发型：长发/短发/发型风格
   - 服饰：裙装/西装/风格倾向
   - 体态：肩宽比例、身形曲线等

2. 环境习惯线索（辅助判断）：
   - 女性常见物品：化妆品、护肤品、发卡发圈、女性饰品、高跟鞋、女性内衣等
   - 男性常见物品：剃须刀、男士护肤品、领带、男性手表、男鞋等
   - 装饰风格：粉色系/可爱风格倾向女性，深色系/简约风格中性
   - 卫浴用品：化妆镜、美妆工具等倾向女性

3. 判断原则：
   - 优先依据直接外观特征
   - 环境线索作为辅助佐证
   - 多个线索指向一致时可提高置信度
   - 线索矛盾或不足时必须输出"无法判断"

【人物体征 evidence 必须包含三要素】
- 参照物：画面中可用于参照的物体（如门框、椅子、桌子、瓶子等），无则写"无明显参照物"
- 全身：是否可见全身轮廓（"可见全身"/"仅上半身"/"仅头肩"/"不可见"）
- 角度影响：拍摄角度对判断的影响（"正面平视/影响小"/"俯拍/影响大"/"仰拍/影响大"/"无法判断"）

如果 evidence 中缺少任何一个要素，身高/体型必须输出"无法判断"，姿态输出"不确定"。

【输出JSON格式】
```json
{{
  "person": {{
    "detected": true/false,
    "count": 数字,
    "height": "偏高/中等/偏矮/无法判断",
    "body_type": "偏瘦/匀称/偏壮/无法判断", 
    "posture": "挚拔/放松/含胸/不确定",
    "gender": "男性/女性/无法判断",
    "gender_evidence": {{
      "appearance": "外观线索：面部/发型/服饰/体态等直接特征",
      "environment": "环境线索：化妆品/剃须刀/饰品等物品线索",
      "consistency": "线索一致性：多个线索是否指向同一结论"
    }},
    "evidence": {{
      "reference": "参照物：...",
      "body_visibility": "全身：...",
      "angle_impact": "角度影响：..."
    }},
    "partial_features": {{
      "hand": "手部特征：手指/手腕/手背特征描述，无则写'未见手部'",
      "arm": "手臂特征：手臂线条/肌肉特征，无则写'未见手臂'",
      "face": "脸部特征：脸型/下巴/轮廓特征，无则写'未见脸部'",
      "neck_shoulder": "颈肩特征：颈部/肩部/锁骨特征，无则写'未见颈肩'",
      "body_type_clue": "体态综合判断：基于以上局部特征的体态推断"
    }},
    "confidence": "low/medium/high"
  }},
  "lifestyle": {{
    "claim": "关于生活方式/消费水平的结论或无法判断",
    "consumption_level": "高消费/中等消费/大众消费/无法判断",
    "accommodation_level": "高档酒店/中档酒店/经济型酒店/租房自住/无法判断",
    "brands_detected": {{
      "clothing": ["识别到的服装品牌"],
      "accessories": ["识别到的配饰/包袋/手表品牌"],
      "electronics": ["识别到的电子产品品牌"],
      "skincare": ["识别到的护肤品/化妆品品牌"],
      "other": ["其他识别到的品牌"]
    }},
    "evidence": ["来自画面：具体依据1", "来自画面：具体依据2"],
    "limitations": ["局限性说明"],
    "confidence": "low/medium"
  }},
  "scene": {{
    "location_type": "室内/室外/无法判断",
    "environment": "具体环境描述",
    "evidence": ["来自画面：具体依据"],
    "confidence": "low/medium"
  }},
  "room_analysis": {{
    "inferred_people_count": "根据环境推断的人数（如：1人/2人/多人/无法判断）",
    "relationship_hint": "关系推断（如：独居/情侣/家庭/合租/无法判断）",
    "evidence": [
      "来自环境：具体依据（如餐具数量、座位数、拖鞋双数、牙刷数量等）"
    ],
    "clues": {{
      "tableware": "餐具/杯子数量线索",
      "seating": "座位/椅子数量线索",
      "personal_items": "个人物品线索（如拖鞋、牙刷、毛巾等）",
      "decoration": "装饰风格线索（如情侣照、儿童用品等）",
      "space_layout": "空间布局线索（如床铺大小、房间数量等）"
    }},
    "limitations": ["环境推断存在较大不确定性，仅供参考"],
    "confidence": "low/medium"
  }},
  "objects": {{
    "detected": ["检测到的物体列表"],
    "brands": ["识别到的品牌（如有）"],
    "evidence": ["来自画面：具体依据"]
  }},
  "intention": {{
    "claim": "照片用途倾向判断或无法判断",
    "evidence": ["来自构图/画面：具体依据"],
    "confidence": "low/medium"
  }},
  "details": {{
    "text_detected": ["画面中识别到的文字"],
    "special_elements": ["特殊元素如反光、水印等"],
    "evidence": ["来自画面：具体依据"]
  }},
  "girlfriend_comments": [
    "朋友风格的可疑点吐槽1，基于画面中的具体物品/细节",
    "朋友风格的可疑点吐槽2，基于画面中的具体物品/细节",
    "如果没有可疑点则输出空数组[]"
  ]
}}
```

【环境推断人数和关系规则】
- 必须基于画面中可见的物品数量/布局进行推断
- 常见线索：餐具数量、座位数、拖鞋双数、牙刷数量、床铺大小、个人物品风格等
- 如线索不足或相互矛盾，必须输出"无法判断"
- clues 中每个字段如无相关线索，填写"未见相关线索"

【环境档次与生活水准判断规则】
1. 酒店/住宿档次判断：
   - 高档：五星级酒店特征（精致装修、高级客房用品、大理石/真皮材质、浴缸或独立淋浴间、欧舒丹/欧莱雅等高端洗护品）
   - 中档：连锁商务酒店特征（标准化装修、正规客房用品、常见品牌洗护品）
   - 经济型：快捷酒店特征（简约装修、基础配置、一次性用品、蓝白色调等）
   - 租房/自住：个人化物品多、长期居住特征

2. 服装品牌判断：
   - 奢侈品：LV、Gucci、Chanel、Hermes、Prada等可识别标志
   - 轻奢：Coach、MK、Kate Spade、Tory Burch等
   - 运动品牌：Nike、Adidas、Lululemon、Under Armour等
   - 快时尚：Zara、H&M、优衣库等
   - 无明显品牌特征则输出"未识别到品牌"

3. 用品品牌判断：
   - 电子产品：iPhone/安卓、Mac/Windows、AirPods等
   - 护肤品：La Mer、SK-II、雅诗兰黛（高端）；兰蔻、雅漾（中端）；大宝、美加净（大众）
   - 包袋、手表、饰品等奢侈品标志
   - 注意：只有明确看到品牌标志才能判断，不要猜测

4. 生活水准综合推断：
   - 高消费：多个奢侈品、高档酒店、高端电子产品
   - 中等消费：中档酒店、运动品牌、中端护肤品
   - 大众消费：经济型酒店、快时尚、基础用品
   - 无法判断：线索不足时必须输出此结果

【重要提醒】
- 如果某项无法从画面获得依据，必须明确输出"无法判断"
- evidence 必须指向画面中的具体元素，不能是推测
- 不要编造或臆测画面中不存在的内容"""

    # 构建用户消息
    user_prompt = "请分析这张照片，按照要求输出JSON格式的分析结果。只输出JSON，不要有其他文字。"
    
    # 如果有额外上下文（如本地检测结果），加入提示
    if extra_context:
        context_str = json.dumps(extra_context, ensure_ascii=False)
        user_prompt += f"\n\n【辅助信息】本地检测器提供的参考：{context_str}"

    # 构建消息
    image_url = _image_to_base64(image_bytes, mime)
    
    messages = [
        {
            "role": "system",
            "content": [{"text": system_prompt}]
        },
        {
            "role": "user",
            "content": [
                {"image": image_url},
                {"text": user_prompt}
            ]
        }
    ]
    
    try:
        # 调用 Qwen VL API
        response = MultiModalConversation.call(
            model=model,
            messages=messages,
        )
        
        if response.status_code == 200:
            content = response.output.choices[0].message.content
            # content 可能是 list 或 str
            if isinstance(content, list):
                text = "".join([item.get("text", "") for item in content if isinstance(item, dict)])
            else:
                text = str(content)
            
            # 尝试解析 JSON
            result = _parse_json_response(text)
            result["_raw_response"] = text
            result["_model"] = model
            result["_success"] = True
            return result
        else:
            return {
                "_success": False,
                "_error": f"API调用失败: {response.code} - {response.message}",
                "_model": model
            }
            
    except Exception as e:
        return {
            "_success": False,
            "_error": f"调用异常: {str(e)}",
            "_model": model
        }


def _parse_json_response(text: str) -> Dict[str, Any]:
    """从模型响应中提取并解析 JSON"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 尝试从 markdown 代码块提取
    import re
    json_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # 尝试找到 { } 包裹的内容
    brace_match = re.search(r'\{[\s\S]*\}', text)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
    
    # 解析失败，返回空结构
    return {
        "_parse_error": True,
        "_raw_text": text
    }


# 同步版本（如果需要）
def analyze_with_qwen_sync(
    image_bytes: bytes,
    mime: str = "image/jpeg",
    model: str = DEFAULT_MODEL,
    extra_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """同步版本的 Qwen VL 分析"""
    import asyncio
    return asyncio.run(analyze_with_qwen(image_bytes, mime, model, extra_context))
