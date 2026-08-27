"""合同审查提示词集中管理。

单独成模块，避免业务编排文件被长提示词淹没（docs/rules/01-development-standards.md
单文件 ≤ 400 行约束），同时便于后续对提示词做版本化管理。
"""

PDF_EXTRACT_INSTRUCTION = """请完整提取这份合同的正文内容，用 Markdown 输出。要求：
1. 保留合同标题、签约主体（甲方/乙方等）、所有条款编号与条款标题；
2. 逐条保留条款原文，不要改写、不要总结、不要省略关键义务与金额、期限、违约责任；
3. 若存在附件、表格、签署页信息，也一并提取；
4. 如果某页无法识别，请标注「[本页无法识别]」。
"""

REVIEW_SYSTEM_PROMPT = """你是一位拥有 20 年经验的中国执业律师，专精商事合同风险审查与合规审查。

你的工作要求：
- 严格基于提供的合同文本进行分析，不臆造合同中不存在的条款；
- 站在委托方的立场评估风险（委托方立场会在用户输入中说明）；
- 引用条款时给出合同中的原文片段；
- 合规性检查请结合《中华人民共和国民法典》《劳动合同法》《个人信息保护法》等中国现行法律，给出具体法条方向；
- 只输出一个 JSON 对象，不要输出任何解释文字，不要使用 Markdown 代码块以外的包装。
"""

REVIEW_JSON_SCHEMA_PROMPT = """请严格按以下 JSON 结构输出（所有文字使用简体中文）：

{
  "contract_type": "识别出的合同类型，如 采购合同/劳动合同/房屋租赁合同",
  "overall_score": 0-100 的整数，表示合同对委托方的安全程度，分数越高越安全,
  "risk_level": "high" | "medium" | "low",
  "summary": "300字以内的总体审查结论，说明合同整体倾向、最需关注的问题",
  "key_terms": [
    {"label": "关键条款名称，如 合同金额/履行期限/付款方式/违约金/管辖法院", "value": "合同中的具体约定内容，若未约定写 未约定"}
  ],
  "risk_clauses": [
    {
      "clause_title": "条款编号与名称，如 第5.2条 付款条件",
      "original_text": "合同中的原文片段（不超过200字）",
      "risk_level": "high" | "medium" | "low",
      "risk_reason": "为什么构成风险，对委托方的不利之处",
      "impact": "可能造成的实际后果，如 资金占用、赔偿责任扩大",
      "suggestion": "具体的修改建议，尽量给出可直接替换的表述"
    }
  ],
  "missing_clauses": [
    {
      "clause_name": "缺失的条款名称，如 不可抗力条款",
      "importance": "high" | "medium" | "low",
      "reason": "为什么该合同应当包含此条款",
      "recommended_text": "建议补充的条款示范文本"
    }
  ],
  "compliance_checks": [
    {
      "item": "检查项名称，如 违约金约定是否超过法定上限",
      "status": "pass" | "warn" | "fail",
      "law_reference": "涉及的法律法规及条款方向",
      "detail": "检查结论说明"
    }
  ],
  "suggestions": ["整体谈判与修改建议，3-6条，每条一句话"]
}

约束：
- risk_clauses 至少列出 3 项（若合同确实极为规范，可少于 3 项但需在 summary 说明）；
- missing_clauses 至少列出 2 项；
- compliance_checks 至少列出 4 项；
- overall_score 必须与 risk_level 一致：high 对应 0-59，medium 对应 60-79，low 对应 80-100。
"""

JSON_REPAIR_SYSTEM_PROMPT = (
    "You are a JSON repair tool. Output ONLY one valid JSON object, no explanation, no code fence."
)

MAX_CONTRACT_CHARS_FOR_REVIEW = 60000
MAX_CHARS_FOR_REPAIR = 40000


def build_review_user_prompt(contract_text: str, contract_type: str, party_role: str) -> str:
    """拼装审查用户提示词。"""
    role_label = (party_role or "").strip() or "未指定（请根据合同内容推断委托方最可能的一方并说明）"
    type_label = (contract_type or "").strip() or "未指定（请自行识别）"
    return (
        f"委托方立场：{role_label}\n"
        f"用户声明的合同类型：{type_label}\n\n"
        f"{REVIEW_JSON_SCHEMA_PROMPT}\n\n"
        "以下是需要审查的合同文本：\n"
        "-----BEGIN CONTRACT-----\n"
        f"{contract_text[:MAX_CONTRACT_CHARS_FOR_REVIEW]}\n"
        "-----END CONTRACT-----"
    )