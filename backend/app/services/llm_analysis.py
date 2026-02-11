# -*- coding: utf-8 -*-
"""LLM 分析服务：多场景下识别「供给方/需求方」并抽取联系方式。"""
import json
import logging
from typing import Any, Dict, List, Optional

from app.config import settings
from app.schemas import (
    ContactSummary,
    LlmLeadsResult,
    PotentialBuyer,
    PotentialSeller,
    UnifiedPost,
)

logger = logging.getLogger(__name__)

# 控制 token：单条正文/评论最大字符数、帖子数上限、每帖评论数上限
MAX_CONTENT_CHARS = 300
MAX_POSTS = 100
MAX_COMMENTS_PER_POST = 30

# 分析场景：三个场景，各配专业 prompt
# 【全局约束】凡涉及账号、联系方式的主体标识，必须展示为完整「昵称（平台号）」格式。
CONTACT_AUTHOR_RULE = (
    "【强制】凡涉及联系方式或账号主体时，主体必须用「昵称（平台号）」完整展示："
    "抖音为「昵称（抖音号）」、小红书为「昵称（小红书号）」、快手为「昵称（快手号）」等。"
    "potential_sellers/potential_buyers 的 author_name 填昵称、author_id 填该平台账号ID（抖音号/小红书号等）；"
    "contacts_summary 的 author_id 必须填该联系方式所属人的完整展示「昵称（平台号）」，不得省略。"
)

SCENARIOS: Dict[str, Dict[str, str]] = {
    "sell_buy": {
        "name": "潜在买家/卖家",
        "seller_label": "潜在卖家",
        "buyer_label": "潜在买家",
        "task": """你扮演**电商/社交线索分析专家**，从给定帖子与评论中抽取可转化的商业线索，输出须严格符合下方规范。

**角色与目标**
- 角色：具备电商与社交流量分析能力的专业分析师。
- 输入：帖子与评论的摘要文本（含作者、正文、评论、签名等）。
- 输出：唯一一个合法 JSON 对象，无 markdown、无多余说明。

**术语与约定**
- **主体标识**：凡涉及账号时，均以「昵称（平台号）」完整展示。author_name 填昵称，author_id 填该平台账号ID（如抖音号、小红书号、快手号）；系统展示时会组合为「昵称（抖音号）」等形式，故两项均须从输入中准确抽取，不得臆造。
- **联系方式**：指微信、电话、私信引导、链接、店铺名等可触达信息；未在原文出现的不得填写。

**一、潜在卖家（potential_sellers）**
- **定义**：在内容中表现出在售货、推广、引流或留联系方式的账号（发帖者或评论者）。
- **纳入标准**：满足任一条即纳入——留微信/电话/私信/链接、明确叫卖或推广、引导私信或加群、签名/简介带联系方式。
- **字段规范**：author_name＝昵称，author_id＝平台号（抖音号/小红书号等）；reason＝一句话判定依据；source_post_id＝来源帖子 id；contacts＝从正文/评论/签名中抽取的联系方式列表，无则 []。同一作者多帖出现合并为一条，contacts 去重。
- **合规**：不臆造任何联系方式；主体必须为「昵称（平台号）」可还原的完整信息。

**二、潜在买家（potential_buyers）**
- **定义**：在内容中表现出购买意向或对商品感兴趣的账号。
- **意向分级（intent_level，必填）**：explicit_inquiry＝明确询价/求购（问价、要链接、求私信、「求」「怎么买」等）；interested＝表达兴趣（种草、心动、想买、好看等未直接求购）；sharing_only＝仅分享/晒单/炫耀；unknown＝与商品或购买无关、无法判断。
- **优先级**：explicit_inquiry、interested 为高价值线索须列入；sharing_only 可列入并标注；unknown 可不列。
- **字段规范**：author_name＝昵称，author_id＝平台号；platform、intent_level、reason、source_post_id、contacts 按规范填写。

**三、联系方式汇总（contacts_summary）**
- 从正文、评论、作者签名中抽取**所有**出现的联系方式，每条一条记录。
- **author_id 必须为「昵称（平台号）」完整格式**，如「张三（抖音号）」「李四（小红书号）」；platform、contact_type（wechat/phone/private_message/other）、value、source（post_content/comment/signature）必填。无则 [].

**四、分析摘要（analysis_summary）**
- 1～3 句话概括：识别卖家/买家数量、高意向买家数量、主要平台与品类（若可推断）。""",
    },
    "hot_products": {
        "name": "潜在热销品",
        "seller_label": "潜在热销品",
        "buyer_label": "相关需求/讨论",
        "task": """你扮演**消费趋势与热销品分析专家**，从帖子与评论中识别有潜力的热销商品/品类，输出须严格符合下方规范。

**角色与目标**
- 角色：具备消费趋势与品类分析能力的专业分析师。
- 输入：帖子与评论的摘要文本。
- 输出：唯一一个合法 JSON 对象，无 markdown、无多余说明。

**一、潜在热销品（potential_sellers）**
- **定义**：在内容中被多次提及、正在热卖或具备爆款潜力的**具体商品/品类/单品**（非账号）。
- **判定维度**：① 声量（多帖/多评论提及同一品）；② 需求信号（求链接、问在哪买、比价）；③ 种草集中（集中夸某品、晒单、推荐）。
- **字段语义**：author_id 与 author_name 均填**品名或品类名**（如「XX 面膜」「露营帐篷」）；platform＝讨论最集中的平台；reason＝热度依据（如「3 帖以上提及」「评论区大量求链接」）；source_post_id＝代表性帖子 id；contacts＝该品相关购买链接/店铺/渠道，无则 []。同品合并，按热度排序；品名简洁可识别。

**二、相关需求/讨论（potential_buyers，可选）**
- 对某品的集中需求或讨论（如「求同款」「哪里买」「平替」）可概括为若干条。author_name＝需求/讨论简述；intent_level＝explicit_inquiry 或 interested；reason、source_post_id、contacts 按需填写。

**三、联系方式汇总（contacts_summary）**
- 仅当正文/评论中明确出现**购买链接、店铺名、购买渠道**时填写。**author_id 必须为「昵称（平台号）」完整格式**（如「张三（抖音号）」），表示该联系方式所属账号；contact_type 用 wechat/phone/private_message/other/link 等。无则 [].

**四、分析摘要（analysis_summary）**
- 1～3 句话概括：潜力品类、热度最高的 1～2 个品、主要需求形态（求链接/晒单/比价等）。""",
    },
    "hot_topics": {
        "name": "热度话题",
        "seller_label": "热度话题",
        "buyer_label": "相关讨论",
        "task": """你扮演**舆情与热点话题分析专家**，从帖子与评论中识别当前高热、高讨论度的话题与关键词，输出须严格符合下方规范。

**角色与目标**
- 角色：具备舆情与热点分析能力的专业分析师。
- 输入：帖子与评论的摘要文本。
- 输出：唯一一个合法 JSON 对象，无 markdown、无多余说明。

**一、热度话题（potential_sellers）**
- **定义**：在给定内容中讨论集中、声量大或具时效性的话题/关键词/事件。
- **判定维度**：多帖/多评论围绕同一主题；评论互动焦点；近期事件、节日、热点词。
- **字段语义**：author_id 与 author_name 均填**话题名或核心关键词**（如「春节出游」「某明星同款」）；platform、reason（热度依据）、source_post_id 按规范填写；contacts 本场景留 []。话题名简洁可检索；同话题合并，按热度排序。

**二、相关讨论（potential_buyers，可选）**
- 子话题、衍生讨论点、对立观点可单独列出。author_name＝子话题/讨论点简述；intent_level＝interested；reason、source_post_id 按需填写；contacts 留 [].

**三、联系方式汇总（contacts_summary）**
- 本场景以话题分析为主，一般不涉及联系方式；无则输出 []. 若确有联系方式需记录，**author_id 须为「昵称（平台号）」完整格式**。

**四、分析摘要（analysis_summary）**
- 1～3 句话概括：主要话题数量、热度最高的 1～2 个、讨论情绪或倾向（若可推断）。""",
    },
}

DEFAULT_SCENE = "sell_buy"

# 输出 JSON 结构说明（所有场景通用，字段名固定）
OUTPUT_JSON_DESC = """
## 输出格式（仅输出一个合法 JSON 对象，禁止 markdown 代码块或前后赘述）

{
  "potential_sellers": [
    { "author_id": "平台号或品名/话题ID", "author_name": "昵称或品名/话题名", "platform": "xhs|dy|ks等", "reason": "判定依据", "source_post_id": "来源帖子id", "contacts": ["联系方式项"] }
  ],
  "potential_buyers": [
    { "author_id": "平台号或空", "author_name": "昵称或简述", "platform": "字符串", "intent_level": "explicit_inquiry|interested|sharing_only|unknown", "reason": "字符串", "source_post_id": "字符串", "contacts": [] }
  ],
  "contacts_summary": [
    { "author_id": "【必填】该联系方式所属人完整展示：昵称（平台号），如 张三（抖音号）", "platform": "字符串", "contact_type": "wechat|phone|private_message|other", "value": "具体值", "source": "post_content|comment|signature" }
  ],
  "analysis_summary": "1～3 句总结"
}

- 未识别到则对应数组为 []。涉及联系方式时 author_id 必须为「昵称（平台号）」完整形式。不要用 ```json 包裹，不要输出 JSON 以外的文字。"""


def _get_system_prompt(scene_id: str) -> str:
    """根据场景 id 生成 system prompt。"""
    scene = SCENARIOS.get(scene_id) or SCENARIOS[DEFAULT_SCENE]
    seller_label = scene["seller_label"]
    buyer_label = scene["buyer_label"]
    task = scene["task"]
    return f"""你是专业的内容分析助手。输入为「帖子与评论」的摘要文本，请严格按下方场景要求分析，并**仅**输出一个合法的 JSON 对象。

{CONTACT_AUTHOR_RULE}

## 本场景映射（字段语义）

- **potential_sellers** 在本场景中表示：{seller_label}
- **potential_buyers** 在本场景中表示：{buyer_label}

## 任务与规则

{task}

""" + OUTPUT_JSON_DESC


def _truncate(s: str, max_len: int) -> str:
    if not s or max_len <= 0:
        return ""
    s = (s or "").strip()
    return s[:max_len] + ("…" if len(s) > max_len else "")


def _build_summary(posts: List[UnifiedPost]) -> str:
    """从帖子列表（含评论）构造给 LLM 的摘要文本。"""
    lines: List[str] = []
    for i, p in enumerate(posts[:MAX_POSTS]):
        if i >= MAX_POSTS:
            break
        title = _truncate(p.title or "", MAX_CONTENT_CHARS)
        content = _truncate(p.content or "", MAX_CONTENT_CHARS)
        author = p.author
        author_name = author.author_name or author.author_id or ""
        signature = _truncate(author.signature or "", 150)
        line = (
            f"[帖子{i+1}] post_id={p.post_id} platform={p.platform} "
            f"作者={author_name} author_id={author.author_id} 签名={signature}\n"
            f"标题: {title}\n正文: {content}\n"
        )
        comments = (p.platform_data or {}).get("comments") or []
        if comments:
            line += "评论:\n"
            for j, c in enumerate(comments[:MAX_COMMENTS_PER_POST]):
                if isinstance(c, dict):
                    cnt = (c.get("content") or "").strip()
                    cnt = _truncate(cnt, MAX_CONTENT_CHARS)
                    auth = c.get("author") or {}
                    c_author_name = auth.get("author_name") or auth.get("author_id") or ""
                    c_author_id = auth.get("author_id") or ""
                    line += f"  - [{j+1}] {c_author_name}({c_author_id}): {cnt}\n"
                else:
                    line += f"  - [{j+1}] (无法解析评论)\n"
        lines.append(line)
    if not lines:
        return "（无帖子内容）"
    return "\n".join(lines)


def _parse_llm_response(text: str) -> LlmLeadsResult:
    """解析 LLM 返回的 JSON 为 LlmLeadsResult。"""
    text = (text or "").strip()
    # 去掉可能的 ```json ... ``` 包裹
    if text.startswith("```"):
        for start in ("```json", "```"):
            if text.startswith(start):
                text = text[len(start):].strip()
                break
        if text.endswith("```"):
            text = text[:-3].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("LLM response JSON parse error: %s", e)
        return LlmLeadsResult()

    def safe_list(val: Any, default: Optional[List] = None) -> List:
        if val is None:
            return default or []
        return list(val) if isinstance(val, (list, tuple)) else (default or [])

    def safe_str(val: Any) -> str:
        return str(val).strip() if val is not None else ""

    sellers: List[PotentialSeller] = []
    for item in safe_list(data.get("potential_sellers")):
        if not isinstance(item, dict):
            continue
        sellers.append(
            PotentialSeller(
                author_id=safe_str(item.get("author_id")),
                author_name=safe_str(item.get("author_name")),
                platform=safe_str(item.get("platform")),
                reason=safe_str(item.get("reason")),
                source_post_id=safe_str(item.get("source_post_id")),
                contacts=[safe_str(x) for x in safe_list(item.get("contacts")) if x],
            )
        )

    buyers: List[PotentialBuyer] = []
    for item in safe_list(data.get("potential_buyers")):
        if not isinstance(item, dict):
            continue
        buyers.append(
            PotentialBuyer(
                author_id=safe_str(item.get("author_id")),
                author_name=safe_str(item.get("author_name")),
                platform=safe_str(item.get("platform")),
                intent_level=safe_str(item.get("intent_level")),
                reason=safe_str(item.get("reason")),
                source_post_id=safe_str(item.get("source_post_id")),
                contacts=[safe_str(x) for x in safe_list(item.get("contacts")) if x],
            )
        )

    contacts_summary: List[ContactSummary] = []
    for item in safe_list(data.get("contacts_summary")):
        if not isinstance(item, dict):
            continue
        contacts_summary.append(
            ContactSummary(
                author_id=safe_str(item.get("author_id")),
                platform=safe_str(item.get("platform")),
                contact_type=safe_str(item.get("contact_type")),
                value=safe_str(item.get("value")),
                source=safe_str(item.get("source")),
            )
        )

    analysis_summary = data.get("analysis_summary")
    if analysis_summary is not None:
        analysis_summary = safe_str(analysis_summary) or None

    return LlmLeadsResult(
        potential_sellers=sellers,
        potential_buyers=buyers,
        contacts_summary=contacts_summary,
        analysis_summary=analysis_summary,
    )


def run_llm_leads_analysis(
    posts: List[UnifiedPost],
    model: str = "deepseek-chat",
    scene: Optional[str] = None,
) -> LlmLeadsResult:
    """
    对帖子列表（含 platform_data.comments）调用 DeepSeek，按场景识别供给方/需求方及联系方式。
    scene 见 SCENARIOS 键，未传或无效时使用默认场景。未配置 API Key 或调用失败时抛出 ValueError。
    """
    scene_id = (scene or "").strip() or DEFAULT_SCENE
    if scene_id not in SCENARIOS:
        scene_id = DEFAULT_SCENE
    logger.info("[LLM分析] 入口: posts=%d 条, scene=%s", len(posts), scene_id)
    if not posts:
        logger.info("[LLM分析] 无帖子，直接返回提示")
        return LlmLeadsResult(analysis_summary="无帖子数据，请先完成搜索或选择历史记录。")

    api_key = (settings.DEEPSEEK_API_KEY or "").strip()
    if not api_key:
        logger.warning("[LLM分析] 未配置 DEEPSEEK_API_KEY")
        raise ValueError("未配置 DEEPSEEK_API_KEY，请在 backend/.env 中设置。")

    model = (model or "deepseek-chat").strip() or "deepseek-chat"
    summary = _build_summary(posts)
    user_prompt = f"以下是从爬取结果中整理的帖子与评论摘要（已截断），请按任务要求输出 JSON。\n\n{summary}"
    logger.info("[LLM分析] 摘要已构建, model=%s, 摘要长度=%d 字符", model, len(summary))

    base_url = (settings.DEEPSEEK_API_BASE or "").strip() or "https://api.deepseek.com"
    if not base_url.startswith("http"):
        base_url = "https://" + base_url
    api_url = base_url.rstrip("/") + "/v1/chat/completions"
    logger.info("[LLM分析] 请求 DeepSeek: %s", api_url)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    system_prompt = _get_system_prompt(scene_id)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }
    if getattr(settings, "DEEPSEEK_ENABLE_SEARCH", False):
        payload["web_search"] = True

    try:
        import httpx
    except ImportError:
        raise ValueError("请安装 httpx 包：pip install httpx") from None

    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.post(api_url, headers=headers, json=payload)
            logger.info("[LLM分析] DeepSeek 响应 status=%d", response.status_code)
            response.raise_for_status()
            result = response.json()
        logger.info("[LLM分析] DeepSeek 返回成功, choices=%d", len(result.get("choices", [])))
    except httpx.TimeoutException as e:
        logger.exception("DeepSeek API timeout")
        raise ValueError("调用 DeepSeek 超时，请稍后重试。") from e
    except httpx.ConnectError as e:
        logger.exception("DeepSeek API connection error")
        raise ValueError(f"无法连接 DeepSeek 服务: {e!s}") from e
    except httpx.HTTPStatusError as e:
        logger.exception("DeepSeek API HTTP error: %s", e)
        try:
            err_body = e.response.json()
            msg = err_body.get("error", {}).get("message", err_body.get("message", str(e)))
        except Exception:
            msg = str(e)
        raise ValueError(f"DeepSeek 接口错误: {msg}") from e
    except Exception as e:
        logger.exception("DeepSeek API call failed")
        raise ValueError(f"调用 DeepSeek 失败: {e!s}") from e

    content = None
    if isinstance(result, dict) and "choices" in result and result["choices"]:
        choice = result["choices"][0]
        msg = choice.get("message") or {}
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
    if not content:
        logger.warning("[LLM分析] 模型未返回 content")
        return LlmLeadsResult(analysis_summary="模型未返回有效内容。")

    logger.info("[LLM分析] 解析 JSON 结果, content 长度=%d", len(content))
    out = _parse_llm_response(content)
    logger.info("[LLM分析] 解析完成: 卖家=%d, 买家=%d, 联系方式=%d", len(out.potential_sellers), len(out.potential_buyers), len(out.contacts_summary))
    return out
