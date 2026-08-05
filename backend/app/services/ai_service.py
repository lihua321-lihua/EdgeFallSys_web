"""
大模型服务网关 —— 统一处理 Qwen 调用、Token 记账、降级、限流

设计核心（三层数据流）：
  调用入口 → _record_call() ─┬─→ LlmCallLog 表（明细，永久，监控事实源）
                             ├─→ Redis api_counter:qwen:{date}（今日高频计数）
                             └─→ ApiUsage qwen 行（today/week/month 累加 + latency 滚动 + cost 累加）
  Celery archive 任务每日凌晨重置 today，从 LlmCallLog 重算 week/month 滚动窗口

降级策略：
  - Key 未配置 → status=degraded，返回默认文本，不报错
  - 日限超限   → status=skipped，返回规则降级文本
  - SDK 缺失/异常 → status=failed，返回规则降级文本
"""
import json
import time
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import LlmCallLog, ApiUsage, AiAnalysisReport


# ============ 内部工具 ============

def _is_qwen_configured() -> bool:
    """判断 DashScope Key 是否已真实配置（非空且非占位符）。"""
    key = settings.qwen_api_key
    return bool(key) and key not in ("your-qwen-api-key", "")


def _calc_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """按配置价目计算单次调用成本（元）。"""
    return round(
        prompt_tokens / 1000 * settings.qwen_price_input_per_1k
        + completion_tokens / 1000 * settings.qwen_price_output_per_1k,
        6,
    )


async def _check_daily_limit() -> bool:
    """读 Redis 今日 token，超 qwen_daily_token_limit 返回 True。

    Redis 不可用时放行（无法准确计数，宁可不限），由 DB 兜底。
    """
    try:
        from app.services.redis_client import get_api_counter
        counter = await get_api_counter("qwen")
        used = counter.get("tokens", 0)
        if used and used >= settings.qwen_daily_token_limit:
            return True
    except Exception:
        pass
    return False


def _usage_tokens(usage) -> tuple[int, int, int]:
    """兼容地提取 (prompt_tokens, completion_tokens, total_tokens)。"""
    if not usage:
        return 0, 0, 0

    def _get(obj, *names):
        for n in names:
            v = getattr(obj, n, None) if not isinstance(obj, dict) else obj.get(n)
            if v:
                return int(v)
        return 0

    p = _get(usage, "input_tokens", "prompt_tokens")
    c = _get(usage, "output_tokens", "completion_tokens")
    t = _get(usage, "total_tokens") or (p + c)
    return p, c, t


async def _record_call(
    db: AsyncSession,
    *,
    endpoint: str,
    status: str,
    latency_ms: int,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    error_msg: Optional[str] = None,
    model: Optional[str] = None,
    request_id: Optional[str] = None,
):
    """记录一次大模型调用：写明细 + upsert 聚合 + Redis 计数。三步互不影响。

    - LlmCallLog：永久明细，监控事实源
    - ApiUsage qwen 行：today/week/month 累加 + latency 滚动加权 + cost 累加；跨天自动重置 today
    - Redis：今日高频计数（限流/实时展示用），失败跳过
    """
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    now_iso = now.isoformat(timespec="seconds")
    cost = _calc_cost(prompt_tokens, completion_tokens)
    used_model = model or settings.qwen_model_name

    # 1. 写明细
    db.add(LlmCallLog(
        request_id=request_id,
        endpoint=endpoint,
        model=used_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        status=status,
        error_msg=error_msg,
        cost_cny=cost,
        created_at=now_iso,
        created_date=today,
    ))

    # 2. upsert ApiUsage qwen 行
    result = await db.execute(select(ApiUsage).where(ApiUsage.service_name == "qwen"))
    record = result.scalar_one_or_none()
    if record is None:
        record = ApiUsage(service_name="qwen", record_date=today)
        db.add(record)
        await db.flush()

    # 跨天重置 today 相关字段（week/month 是滚动窗口，archive 任务会重算纠正）
    if record.record_date != today:
        record.record_date = today
        record.calls_today = 0
        record.api_calls_today = 0
        record.tokens_today = 0
        record.cost_estimate = 0.0

    record.api_calls_today = (record.api_calls_today or 0) + 1
    record.tokens_today = (record.tokens_today or 0) + total_tokens
    record.tokens_week = (record.tokens_week or 0) + total_tokens
    record.tokens_month = (record.tokens_month or 0) + total_tokens
    record.cost_estimate = (record.cost_estimate or 0.0) + cost
    # latency 滚动加权平均（按本次调用后的累计次数）
    n = record.api_calls_today
    if n <= 1:
        record.latency_ms = latency_ms
    else:
        record.latency_ms = int((record.latency_ms * (n - 1) + latency_ms) / n)
    await db.flush()

    # 3. Redis 计数（失败跳过，DB 已记账不丢）
    try:
        from app.services.redis_client import increment_api_counter
        await increment_api_counter("qwen", "api_calls", 1)
        if total_tokens:
            await increment_api_counter("qwen", "tokens", total_tokens)
    except Exception:
        pass


# ============ 告警智能分类 ============

CLASSIFY_PROMPT = """你是一位乡村养老安全告警分析助手。请根据以下告警信息进行分类并给出处置建议。

告警类型：{alert_type}
告警描述：{alert_text}
老人背景：{elder_context}

请严格只返回如下 JSON（不要任何额外文字或代码块标记）：
{{"category": "分类", "severity": "级别", "suggestion": "处置建议"}}

分类可选值：跌倒 / 诈骗 / 入侵 / 健康异常 / 误报
级别可选值：critical / high / medium / low
处置建议不超过 50 字，用村干部能听懂的大白话。"""


def _rule_based_classify(alert_type: str, alert_text: str = "") -> dict:
    """Key 未配置/超限/失败时的降级分类（基于 alert_type 关键词）。"""
    rules = {
        "FALL_DETECTED": {
            "category": "跌倒",
            "severity": "critical",
            "suggestion": "立即联系老人确认情况，必要时上门查看；若无法联系，紧急通知家属或送医。",
        },
        "SCAM_ALERT": {
            "category": "诈骗",
            "severity": "high",
            "suggestion": "提醒老人切勿转账，立即联系家属确认，必要时报警。",
        },
        "INTRUSION_ALERT": {
            "category": "入侵",
            "severity": "high",
            "suggestion": "查看摄像头画面确认是否为陌生人，必要时报警。",
        },
        "HEALTH_ABNORMAL": {
            "category": "健康异常",
            "severity": "high",
            "suggestion": "联系村医上门查看老人身体状况，必要时送医。",
        },
    }
    return rules.get(alert_type, {
        "category": "待确认",
        "severity": "medium",
        "suggestion": "请人工核实告警详情并处置。",
    })


def _parse_classify_json(text: str) -> Optional[dict]:
    """从大模型返回中提取 JSON（兼容 markdown 代码块包裹）。"""
    s = text.strip()
    if s.startswith("```"):
        # 去掉 ```json ... ``` 包裹
        s = s.split("\n", 1)[-1] if "\n" in s else s
        s = s.rsplit("```", 1)[0].strip()
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return None


async def classify_alert(
    db: AsyncSession,
    alert_type: str,
    alert_text: str = "",
    elder_context: str = "",
    request_id: Optional[str] = None,
) -> dict:
    """告警智能分类。Key 未配置/超限/失败均降级为规则分类，不报错。"""
    # 未配置 → 降级
    if not _is_qwen_configured():
        result = _rule_based_classify(alert_type, alert_text)
        await _record_call(
            db, endpoint="classify_alert", status="degraded", latency_ms=0,
            completion_tokens=len(json.dumps(result, ensure_ascii=False)),
            total_tokens=len(json.dumps(result, ensure_ascii=False)),
            error_msg="qwen api key not configured", request_id=request_id,
        )
        return result

    # 日限超限 → 降级
    if await _check_daily_limit():
        result = _rule_based_classify(alert_type, alert_text)
        await _record_call(
            db, endpoint="classify_alert", status="skipped", latency_ms=0,
            completion_tokens=len(json.dumps(result, ensure_ascii=False)),
            total_tokens=len(json.dumps(result, ensure_ascii=False)),
            error_msg="daily token limit exceeded", request_id=request_id,
        )
        return result

    prompt = CLASSIFY_PROMPT.format(
        alert_type=alert_type,
        alert_text=alert_text or "（无）",
        elder_context=elder_context or "（无）",
    )
    start = time.time()
    try:
        from dashscope import Generation
        response = await asyncio.to_thread(
            Generation.call,
            model=settings.qwen_model_name,
            prompt=prompt,
            api_key=settings.qwen_api_key,
        )
        latency_ms = int((time.time() - start) * 1000)

        if response.status_code == 200:
            text = (response.output.text or "").strip() if response.output else ""
            p, c, t = _usage_tokens(getattr(response, "usage", None))
            parsed = _parse_classify_json(text)
            if parsed:
                result = {
                    "category": parsed.get("category", "待确认"),
                    "severity": parsed.get("severity", "medium"),
                    "suggestion": parsed.get("suggestion", ""),
                }
            else:
                # JSON 解析失败，降级但带上原文
                result = _rule_based_classify(alert_type, alert_text)
                result["suggestion"] = text[:200] or result["suggestion"]
            await _record_call(
                db, endpoint="classify_alert", status="success", latency_ms=latency_ms,
                prompt_tokens=p, completion_tokens=c, total_tokens=t, request_id=request_id,
            )
            return result
        else:
            msg = getattr(response, "message", "调用失败")
            await _record_call(
                db, endpoint="classify_alert", status="failed", latency_ms=latency_ms,
                error_msg=msg, request_id=request_id,
            )
            return _rule_based_classify(alert_type, alert_text)

    except ImportError:
        await _record_call(
            db, endpoint="classify_alert", status="failed", latency_ms=0,
            error_msg="dashscope SDK 未安装", request_id=request_id,
        )
        return _rule_based_classify(alert_type, alert_text)
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        await _record_call(
            db, endpoint="classify_alert", status="failed", latency_ms=latency_ms,
            error_msg=str(e), request_id=request_id,
        )
        return _rule_based_classify(alert_type, alert_text)


# ============ 流式对话（SSE） ============

def _sse_chunk(text: str) -> str:
    return f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"


def _sse_done() -> str:
    return "data: [DONE]\n\n"


async def stream_chat(
    db: AsyncSession,
    message: str,
    history: Optional[list] = None,
) -> AsyncGenerator[str, None]:
    """SSE 流式对话。yield 形如 'data: {"text":"..."}\\n\\n' 的字符串，末尾 'data: [DONE]\\n\\n'。"""
    # 未配置 → 降级单段文本
    if not _is_qwen_configured():
        fallback = "（大模型未配置）我已收到您的消息，但当前未接入大模型服务，无法进行智能对话。请配置 DashScope API Key 后重试。"
        yield _sse_chunk(fallback)
        await _record_call(
            db, endpoint="chat", status="degraded", latency_ms=0,
            completion_tokens=len(fallback), total_tokens=len(fallback),
            error_msg="qwen api key not configured",
        )
        yield _sse_done()
        return

    # 日限超限 → 降级
    if await _check_daily_limit():
        fallback = "今日大模型 Token 用量已达上限，已自动降级。请明日再试或联系管理员调整限额。"
        yield _sse_chunk(fallback)
        await _record_call(
            db, endpoint="chat", status="skipped", latency_ms=0,
            completion_tokens=len(fallback), total_tokens=len(fallback),
            error_msg="daily token limit exceeded",
        )
        yield _sse_done()
        return

    # 组装 messages（保留最近 10 轮历史）
    messages = []
    if history:
        for h in history[-10:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    loop = asyncio.get_event_loop()
    q: asyncio.Queue = asyncio.Queue()
    start = time.time()

    def _producer():
        """在线程中跑 dashscope 同步流式迭代器，通过 queue 把 chunk 传回异步侧。"""
        try:
            from dashscope import Generation
            responses = Generation.call(
                model=settings.qwen_model_name,
                messages=messages,
                stream=True,
                incremental_output=True,
                api_key=settings.qwen_api_key,
            )
            full_text = ""
            usage = None
            for resp in responses:
                if resp.status_code == 200:
                    chunk = (resp.output.text if resp.output else "") or ""
                    if chunk:
                        full_text += chunk
                        asyncio.run_coroutine_threadsafe(q.put(("chunk", chunk)), loop)
                    if getattr(resp, "usage", None):
                        usage = resp.usage
                else:
                    asyncio.run_coroutine_threadsafe(
                        q.put(("error", getattr(resp, "message", "调用失败"))), loop
                    )
                    return
            asyncio.run_coroutine_threadsafe(q.put(("done", full_text, usage)), loop)
        except ImportError:
            asyncio.run_coroutine_threadsafe(q.put(("error", "dashscope SDK 未安装")), loop)
        except Exception as e:
            asyncio.run_coroutine_threadsafe(q.put(("error", str(e))), loop)

    threading.Thread(target=_producer, daemon=True).start()

    full_text = ""
    status = "success"
    error_msg = None
    usage = None
    while True:
        try:
            item = await asyncio.wait_for(q.get(), timeout=60.0)
        except asyncio.TimeoutError:
            error_msg = "流式响应超时"
            status = "failed"
            break
        tag = item[0]
        if tag == "chunk":
            full_text += item[1]
            yield _sse_chunk(item[1])
        elif tag == "done":
            full_text = item[1] or full_text
            usage = item[2]
            break
        elif tag == "error":
            error_msg = item[1]
            status = "failed"
            break

    latency_ms = int((time.time() - start) * 1000)
    p, c, t = _usage_tokens(usage)
    if not t:
        # 无 usage 时用字符数近似
        c = len(full_text)
        t = c
    await _record_call(
        db, endpoint="chat", status=status, latency_ms=latency_ms,
        prompt_tokens=p, completion_tokens=c, total_tokens=t, error_msg=error_msg,
    )
    yield _sse_done()


# ============ 健康报告生成（带记账） ============

HEALTH_REPORT_PROMPT = """你是一位专业的乡村养老健康顾问。请根据以下老人的监测数据，生成一份月度健康评估报告。

老人信息：{elder_name}，{age}岁，{gender}
本月数据摘要：{data_summary}

请用通俗易懂的语言（村干部能看懂），不超过 200 字，包含：
1. 整体状态评价（一句话）
2. 需要关注的风险点（如有）
3. 建议措施（1-2 条）

不要使用"语速""泛音""基频"等专业术语。不要给出医疗诊断。"""


async def generate_health_report_v2(
    db: AsyncSession,
    elder_name: str,
    age: int,
    gender: str,
    data_summary: str,
    request_id: Optional[str] = None,
) -> str:
    """生成健康报告并记账。Key 未配置/失败时返回默认文本。"""
    if not _is_qwen_configured():
        text = f"经系统分析，{elder_name}本月整体状况良好。建议保持现有生活习惯，关注季节变化。（大模型 API 未配置，此为默认文本）"
        await _record_call(
            db, endpoint="health_report", status="degraded", latency_ms=0,
            completion_tokens=len(text), total_tokens=len(text),
            error_msg="qwen api key not configured", request_id=request_id,
        )
        return text

    if await _check_daily_limit():
        text = f"经系统分析，{elder_name}本月整体状况良好。（Token 日限已达，已降级返回默认文本）"
        await _record_call(
            db, endpoint="health_report", status="skipped", latency_ms=0,
            completion_tokens=len(text), total_tokens=len(text),
            error_msg="daily token limit exceeded", request_id=request_id,
        )
        return text

    prompt = HEALTH_REPORT_PROMPT.format(
        elder_name=elder_name, age=age, gender=gender, data_summary=data_summary,
    )
    start = time.time()
    try:
        from dashscope import Generation
        response = await asyncio.to_thread(
            Generation.call,
            model=settings.qwen_model_name,
            prompt=prompt,
            max_tokens=300,
            temperature=0.7,
            api_key=settings.qwen_api_key,
        )
        latency_ms = int((time.time() - start) * 1000)

        if response.status_code == 200:
            text = (response.output.text or "").strip() if response.output else ""
            p, c, t = _usage_tokens(getattr(response, "usage", None))
            await _record_call(
                db, endpoint="health_report", status="success", latency_ms=latency_ms,
                prompt_tokens=p, completion_tokens=c, total_tokens=t, request_id=request_id,
            )
            return text or f"经系统分析，{elder_name}本月整体状况良好。"
        else:
            msg = getattr(response, "message", "调用失败")
            await _record_call(
                db, endpoint="health_report", status="failed", latency_ms=latency_ms,
                error_msg=msg, request_id=request_id,
            )
            return f"经系统分析，{elder_name}本月整体状况良好。（AI 报告生成失败，此为默认文本）"
    except ImportError:
        await _record_call(
            db, endpoint="health_report", status="failed", latency_ms=0,
            error_msg="dashscope SDK 未安装", request_id=request_id,
        )
        return f"经系统分析，{elder_name}本月整体状况良好。（dashscope SDK 未安装）"
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        await _record_call(
            db, endpoint="health_report", status="failed", latency_ms=latency_ms,
            error_msg=str(e), request_id=request_id,
        )
        return f"经系统分析，{elder_name}本月整体状况良好。（AI 报告生成异常）"


# ============================================================
# 专业 AI 分析报告：跌倒救援简报 + 长期健康分析
# ============================================================
# 两类报告均为固定模块结构化 JSON，由大模型生成；断网/Key 未配置/置信度不足/超限
# 时走本地模板兜底（source=fallback），不阻断业务。固定 temperature=0 + seed 保证可复现。
# 仅传输纯文本/数值结构化数据，不上传任何影像隐私内容。

# 救援简报 9 模块固定字段名
RESCUE_BRIEFING_KEYS = [
    "event_overview", "injury_assessment", "vital_signs_reading",
    "first_aid_by_group", "medication_risk", "transfer_precautions",
    "contact_priority", "observation_72h", "home_fall_prevention",
]

# 长期健康分析 10 模块固定字段名
HEALTH_ANALYSIS_KEYS = [
    "overall_assessment", "cardiovascular_risk", "fall_root_cause",
    "medication_compliance", "activity_sleep", "high_risk_list",
    "tiered_intervention", "village_doctor_followup", "family_care_advice",
    "trend_forecast_review",
]

RESCUE_BRIEFING_PROMPT = """你是一位具备老年急救医学专业背景的乡村养老应急救援顾问。请根据以下跌倒事件结构化数据，生成一份标准化智能救援简报。

【跌倒事件数据】
{fall_data_text}

【要求】
1. 以老年急救医学专业视角做多层级伤势风险评估，区分普通损伤与危重最坏情况。
2. 输出适配农村医疗资源薄弱的现实场景，语言兼顾村医、家属能看懂的大白话。
3. 严格只返回如下 JSON 对象（不要任何 markdown 标记、代码块、额外文字或解释）：
{{
  "event_overview": "事件概述：跌倒时间、地点、老人基本信息、跌倒经过简述",
  "injury_assessment": "伤势评估：多层级风险（普通损伤/危重最坏情况）、可能受伤部位、严重程度判断",
  "vital_signs_reading": "生命体征解读：心率/血氧/体温/血压的异常判读与临床意义",
  "first_aid_by_group": "分人群现场急救方案：网格员/村医/家属各自应做的处置步骤",
  "medication_risk": "用药风险提醒：结合既往用药的禁忌与相互作用风险",
  "transfer_precautions": "就医转运注意事项：是否需转院、转运体位、途中监护要点",
  "contact_priority": "联系人通知排序：按紧急程度排序的通知对象与顺序",
  "observation_72h": "72小时观察重点：需警惕的迟发症状与复查时点",
  "home_fall_prevention": "居家环境防跌倒优化建议：针对本次跌倒位置的改造建议"
}}
4. 每个字段值为一句话或一段话，不超过 200 字，使用中文。"""

HEALTH_ANALYSIS_PROMPT = """你是一位具备老年医学与公共卫生背景的乡村养老健康顾问。请根据以下老人长期健康监测历史数据，生成一份长期健康数据分析报告。

【老人健康监测数据】
{health_data_text}

【要求】
1. 从心血管风险、跌倒隐患、服药依从性、活动/睡眠状态多维度做长期趋势研判，标记高危预警信号。
2. 报告用于网页端长期健康档案展示，给村委、家属提供长效照护指导，语言通俗。
3. 严格只返回如下 JSON 对象（不要任何 markdown 标记、代码块、额外文字或解释）：
{{
  "overall_assessment": "健康综合评估：整体状态一句话总结与综合风险等级",
  "cardiovascular_risk": "心血管风险分析：血压/心率趋势、心血管事件风险研判",
  "fall_root_cause": "跌倒深层诱因分析：结合病史/用药/活动量的跌倒成因",
  "medication_compliance": "用药合规提醒：服药依从性评估与漏服/错服风险",
  "activity_sleep": "活动/睡眠评估：日均步数、睡眠时长的趋势与异常",
  "high_risk_list": "高危预警清单：需立即关注的风险项列表（数组或文本）",
  "tiered_intervention": "分级干预措施：按高/中/低风险分级的具体干预动作",
  "village_doctor_followup": "村医随访计划：随访频次、重点检查项、下次随访建议",
  "family_care_advice": "子女日常关怀建议：家属可执行的日常照护要点",
  "trend_forecast_review": "长期趋势预测与复查建议：未来风险走势与复查周期建议"
}}
4. 每个字段值为一句话或一段话，不超过 200 字，使用中文。"""


def _should_call_llm(confidence: Optional[float], force_fallback: bool = False) -> tuple[bool, str]:
    """跌倒置信度门控 + Key 配置 + 日限三重校验。

    返回 (是否可调大模型, 不可调时的原因)。force_fallback 或 confidence < 阈值 → 直接走兜底，
    满足"断网不依赖大模型、改用本地基础模板兜底"。
    """
    if force_fallback:
        return False, "force_fallback"
    # 救援简报必须置信度达标（健康分析不传 confidence 视为达标）
    if confidence is not None and confidence < settings.ai_report_fall_confidence_threshold:
        return False, f"confidence {confidence} < threshold {settings.ai_report_fall_confidence_threshold}"
    if not _is_qwen_configured():
        return False, "qwen api key not configured"
    # 日限检查需异步，此处仅做配置/置信度门控；日限在调用前再异步校验
    return True, ""


def _parse_strict_json(text: str, required_keys: list[str]) -> Optional[dict]:
    """严格 JSON 解析：去 markdown 包裹 + json.loads + 必需字段校验。"""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1] if "\n" in s else s
        s = s.rsplit("```", 1)[0].strip()
    # 容错：截取首个 { 到末尾 } 之间的内容
    if s and not s.startswith("{"):
        first = s.find("{")
        last = s.rfind("}")
        if first != -1 and last != -1 and last > first:
            s = s[first:last + 1]
    try:
        obj = json.loads(s)
        if isinstance(obj, dict) and all(k in obj for k in required_keys):
            return obj
    except Exception:
        pass
    return None


def _report_to_txt(report: dict, key_titles: list[tuple[str, str]]) -> str:
    """将结构化 JSON 报告转为可读 TXT（标题 + 缩进段落）。"""
    lines = []
    for key, title in key_titles:
        val = report.get(key, "")
        if isinstance(val, (list, dict)):
            val = json.dumps(val, ensure_ascii=False, indent=2)
        lines.append(f"【{title}】")
        lines.append(str(val) if val else "（无）")
        lines.append("")
    return "\n".join(lines).strip()


def _save_report_files(
    report_type: str, elder_id: str, report_obj: dict, report_txt: str,
) -> tuple[str, str]:
    """写 JSON + TXT 文件到存档目录，返回 (json_path, txt_path)。失败时返回空串不阻断。"""
    storage_dir = Path(settings.ai_report_storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{report_type}_{elder_id}_{ts}"
    json_path = storage_dir / f"{base}.json"
    txt_path = storage_dir / f"{base}.txt"
    try:
        json_path.write_text(json.dumps(report_obj, ensure_ascii=False, indent=2), encoding="utf-8")
        txt_path.write_text(report_txt, encoding="utf-8")
        return str(json_path), str(txt_path)
    except Exception as e:
        print(f"[AI_REPORT] 文件存档失败: {e}")
        return "", ""


def _store_report(
    db: AsyncSession, *, report_type: str, elder_id: str, event_id: Optional[str],
    report_obj: dict, report_txt: str, source: str, confidence: Optional[float],
    request_id: Optional[str],
) -> AiAnalysisReport:
    """落库 AiAnalysisReport + 写文件，返回 ORM 对象。"""
    now = datetime.now()
    json_path, txt_path = _save_report_files(report_type, elder_id, report_obj, report_txt)
    report = AiAnalysisReport(
        report_type=report_type,
        elder_id=elder_id,
        event_id=event_id,
        report_json=json.dumps(report_obj, ensure_ascii=False),
        report_txt=report_txt,
        json_file_path=json_path,
        txt_file_path=txt_path,
        source=source,
        confidence=confidence,
        model=settings.qwen_model_name if source == "qwen" else None,
        request_id=request_id,
        created_at=now.isoformat(timespec="seconds"),
        created_date=now.strftime("%Y-%m-%d"),
    )
    db.add(report)
    return report


# ---------- 救援简报本地兜底 ----------

RESCUE_BRIEFING_TITLES = list(zip(RESCUE_BRIEFING_KEYS, [
    "事件概述", "伤势评估", "生命体征解读", "分人群现场急救方案", "用药风险提醒",
    "就医转运注意事项", "联系人通知排序", "72小时观察重点", "居家环境防跌倒优化建议",
]))


def _rescue_briefing_fallback(fall_data: dict) -> dict:
    """本地模板兜底：基于规则填充 9 模块（断网/Key 未配置/置信度不足/超限/失败时使用）。"""
    vs = fall_data.get("vital_signs") or {}
    accel = fall_data.get("acceleration")
    # 伤势分级：加速度 > 3g 视为高危
    if accel and accel > 3.0:
        injury = "高危：跌倒冲击较大，可能存在骨折或颅脑损伤，需立即上门查看并准备送医。"
    elif accel and accel > 1.5:
        injury = "中危：跌倒冲击中等，警惕软组织损伤与迟发症状，建议村医上门评估。"
    else:
        injury = "低危：跌倒冲击较小，但老年人需警惕迟发性损伤，建议观察。"

    hr = vs.get("heart_rate")
    spo2 = vs.get("spo2")
    vs_text = []
    if hr: vs_text.append(f"心率 {hr} bpm（{'偏快' if hr > 100 else '偏慢' if hr < 50 else '正常'}）")
    if spo2: vs_text.append(f"血氧 {spo2}%（{'偏低需警惕' if spo2 < 92 else '正常'}）")
    if vs.get("temperature"): vs_text.append(f"体温 {vs['temperature']}℃")
    if vs.get("blood_pressure"): vs_text.append(f"血压 {vs['blood_pressure']}")
    vs_reading = "；".join(vs_text) if vs_text else "暂无生命体征数据，建议尽快测量。"

    contact = fall_data.get("emergency_relation") or "家属"
    return {
        "event_overview": f"老人于 {fall_data.get('fall_time', '未知时间')} 在 {fall_data.get('fall_location', '家中')} 发生跌倒，加速度峰值 {accel or '未知'} g，置信度 {fall_data.get('confidence', '未知')}。",
        "injury_assessment": injury,
        "vital_signs_reading": vs_reading,
        "first_aid_by_group": "网格员：立即上门确认老人意识与活动能力；村医：评估生命体征与外伤，判断是否需送医；家属：保持电话沟通，安抚老人情绪。",
        "medication_risk": f"结合既往用药（{fall_data.get('current_medications') or '未提供'}），注意降压药、抗凝药可能加重跌倒后出血风险。",
        "transfer_precautions": "若老人无法站立或意识不清，勿强行搬动，平卧保暖，等待专业转运；疑似骨折需固定后转运。",
        "contact_priority": f"1. {contact}（紧急联系人）；2. 村医上门评估；3. 必要时拨打 120 送乡镇卫生院。",
        "observation_72h": "72 小时内重点观察：意识变化、头痛呕吐（警惕颅脑损伤）、肢体活动障碍、隐性出血，出现上述症状立即送医。",
        "home_fall_prevention": f"针对 {fall_data.get('fall_location', '跌倒位置')}：加装防滑垫、夜灯、扶手；清理地面杂物与积水；卫生间建议使用沐浴椅。",
    }


# ---------- 长期健康分析本地兜底 ----------

HEALTH_ANALYSIS_TITLES = list(zip(HEALTH_ANALYSIS_KEYS, [
    "健康综合评估", "心血管风险分析", "跌倒深层诱因分析", "用药合规提醒", "活动/睡眠评估",
    "高危预警清单", "分级干预措施", "村医随访计划", "子女日常关怀建议", "长期趋势预测与复查建议",
]))


def _health_analysis_fallback(health_data: dict) -> dict:
    """本地模板兜底：基于阈值规则填充 10 模块。"""
    hr = health_data.get("hr_history") or ""
    steps_avg = health_data.get("steps_avg")
    sleep = health_data.get("sleep_hours")
    risks = []
    if "100" in hr or "110" in hr: risks.append("心率偏快趋势，警惕心血管事件")
    if steps_avg and steps_avg < 1000: risks.append("日均步数过低，活动量不足")
    if sleep and sleep < 5: risks.append("睡眠不足，跌倒风险升高")
    risk_text = "；".join(risks) if risks else "暂未见明显高危信号"

    return {
        "overall_assessment": f"近 {health_data.get('data_period', '30天')} 健康综合状态：{('存在风险需关注' if risks else '基本平稳')}。",
        "cardiovascular_risk": f"心率历史：{hr or '无数据'}。建议定期监测血压，警惕心律失常与血压波动。",
        "fall_root_cause": f"结合活动量（日均 {steps_avg or '未知'} 步）与睡眠（日均 {sleep or '未知'} 小时），跌倒诱因可能与活动量不足、夜间起夜有关。",
        "medication_compliance": f"服药记录：{health_data.get('medication_records', '未提供')}。需关注漏服与重复服药风险，建议使用分药盒。",
        "activity_sleep": f"日均步数 {steps_avg or '未知'}，日均睡眠 {sleep or '未知'} 小时。{('活动量偏低需鼓励适度活动' if steps_avg and steps_avg < 1000 else '活动量尚可')}。",
        "high_risk_list": risk_text,
        "tiered_intervention": "高风险：心血管异常需村医上门复查；中风险：活动量不足建议每日散步；低风险：维持现有生活习惯。",
        "village_doctor_followup": "建议村医每周随访 1 次，重点测量血压心率，每月复查一次用药情况。",
        "family_care_advice": "子女每日电话问候，关注老人饮食与情绪；协助整理药品；节假日陪伴就医复查。",
        "trend_forecast_review": "若现状持续，心血管与跌倒风险将缓慢上升，建议每 3 个月复查一次健康档案。",
    }


# ---------- 核心生成函数 ----------

async def _call_qwen_for_report(
    db: AsyncSession, *, endpoint: str, prompt: str, required_keys: list[str],
    request_id: Optional[str], fallback_obj: dict,
) -> tuple[dict, str, int, int, int, Optional[str]]:
    """通用大模型报告生成调用。返回 (report_obj, source, prompt_tokens, completion_tokens, total_tokens, error_msg)。

    成功 → source=qwen；失败/超限 → source=fallback + 对应 error_msg。记账由调用方完成。
    """
    if await _check_daily_limit():
        return fallback_obj, "fallback", 0, 0, 0, "daily token limit exceeded"

    start = time.time()
    try:
        from dashscope import Generation
        response = await asyncio.to_thread(
            Generation.call,
            model=settings.qwen_model_name,
            messages=[{"role": "user", "content": prompt}],
            result_format="message",
            temperature=0,       # 固定参数保证可复现
            seed=1234,
            api_key=settings.qwen_api_key,
        )
        latency_ms = int((time.time() - start) * 1000)

        if response.status_code == 200:
            text = (response.output.choices[0].message.content or "").strip() if response.output else ""
            p, c, t = _usage_tokens(getattr(response, "usage", None))
            parsed = _parse_strict_json(text, required_keys)
            if parsed:
                return parsed, "qwen", p, c, t, None
            # JSON 解析失败，降级但记账为 failed
            return fallback_obj, "fallback", p, c, t, f"json parse failed, raw: {text[:200]}"
        else:
            msg = getattr(response, "message", "调用失败")
            return fallback_obj, "fallback", 0, 0, 0, msg
    except ImportError:
        return fallback_obj, "fallback", 0, 0, 0, "dashscope SDK 未安装"
    except Exception as e:
        return fallback_obj, "fallback", 0, 0, 0, str(e)


async def generate_rescue_briefing(
    db: AsyncSession,
    elder_id: str,
    fall_data: dict,
    request_id: Optional[str] = None,
    event_id: Optional[str] = None,
    confidence: Optional[float] = None,
    force_fallback: bool = False,
) -> dict:
    """生成跌倒救援简报（9 模块 JSON）。置信度不足/断网/Key 未配置/超限/失败均走本地兜底。

    返回 {report_id, report_json, report_txt, source, confidence, ...}。
    """
    fall_data = {**fall_data, "confidence": confidence}
    fallback_obj = _rescue_briefing_fallback(fall_data)

    can_call, reason = _should_call_llm(confidence, force_fallback)
    if not can_call:
        report_txt = _report_to_txt(fallback_obj, RESCUE_BRIEFING_TITLES)
        report = _store_report(
            db, report_type="rescue_briefing", elder_id=elder_id, event_id=event_id,
            report_obj=fallback_obj, report_txt=report_txt, source="fallback",
            confidence=confidence, request_id=request_id,
        )
        await db.flush()
        await _record_call(
            db, endpoint="rescue_briefing", status="degraded", latency_ms=0,
            completion_tokens=len(json.dumps(fallback_obj, ensure_ascii=False)),
            total_tokens=len(json.dumps(fallback_obj, ensure_ascii=False)),
            error_msg=reason, request_id=request_id,
        )
        return _report_response(report, fallback_obj)

    fall_data_text = json.dumps(fall_data, ensure_ascii=False, indent=2)
    prompt = RESCUE_BRIEFING_PROMPT.format(fall_data_text=fall_data_text)
    start = time.time()
    report_obj, source, p, c, t, err = await _call_qwen_for_report(
        db, endpoint="rescue_briefing", prompt=prompt, required_keys=RESCUE_BRIEFING_KEYS,
        request_id=request_id, fallback_obj=fallback_obj,
    )
    latency_ms = int((time.time() - start) * 1000)
    report_txt = _report_to_txt(report_obj, RESCUE_BRIEFING_TITLES)
    report = _store_report(
        db, report_type="rescue_briefing", elder_id=elder_id, event_id=event_id,
        report_obj=report_obj, report_txt=report_txt, source=source,
        confidence=confidence, request_id=request_id,
    )
    await db.flush()
    await _record_call(
        db, endpoint="rescue_briefing",
        status="success" if source == "qwen" else "failed",
        latency_ms=latency_ms, prompt_tokens=p, completion_tokens=c, total_tokens=t,
        error_msg=err, request_id=request_id,
    )
    return _report_response(report, report_obj)


async def generate_health_analysis(
    db: AsyncSession,
    elder_id: str,
    health_data: dict,
    request_id: Optional[str] = None,
    force_fallback: bool = False,
) -> dict:
    """生成长期健康数据分析报告（10 模块 JSON）。Key 未配置/超限/失败均走本地兜底。

    健康分析不校验置信度（非跌倒事件），仅校验 Key 与日限。
    """
    fallback_obj = _health_analysis_fallback(health_data)

    can_call, reason = _should_call_llm(confidence=None, force_fallback=force_fallback)
    if not can_call:
        report_txt = _report_to_txt(fallback_obj, HEALTH_ANALYSIS_TITLES)
        report = _store_report(
            db, report_type="health_analysis", elder_id=elder_id, event_id=None,
            report_obj=fallback_obj, report_txt=report_txt, source="fallback",
            confidence=None, request_id=request_id,
        )
        await db.flush()
        await _record_call(
            db, endpoint="health_analysis", status="degraded", latency_ms=0,
            completion_tokens=len(json.dumps(fallback_obj, ensure_ascii=False)),
            total_tokens=len(json.dumps(fallback_obj, ensure_ascii=False)),
            error_msg=reason, request_id=request_id,
        )
        return _report_response(report, fallback_obj)

    health_data_text = json.dumps(health_data, ensure_ascii=False, indent=2)
    prompt = HEALTH_ANALYSIS_PROMPT.format(health_data_text=health_data_text)
    start = time.time()
    report_obj, source, p, c, t, err = await _call_qwen_for_report(
        db, endpoint="health_analysis", prompt=prompt, required_keys=HEALTH_ANALYSIS_KEYS,
        request_id=request_id, fallback_obj=fallback_obj,
    )
    latency_ms = int((time.time() - start) * 1000)
    report_txt = _report_to_txt(report_obj, HEALTH_ANALYSIS_TITLES)
    report = _store_report(
        db, report_type="health_analysis", elder_id=elder_id, event_id=None,
        report_obj=report_obj, report_txt=report_txt, source=source,
        confidence=None, request_id=request_id,
    )
    await db.flush()
    await _record_call(
        db, endpoint="health_analysis",
        status="success" if source == "qwen" else "failed",
        latency_ms=latency_ms, prompt_tokens=p, completion_tokens=c, total_tokens=t,
        error_msg=err, request_id=request_id,
    )
    return _report_response(report, report_obj)


def _report_response(report: AiAnalysisReport, report_obj: dict) -> dict:
    """构造返回给路由层的响应字典。"""
    return {
        "report_id": report.id,
        "report_type": report.report_type,
        "elder_id": report.elder_id,
        "event_id": report.event_id,
        "report": report_obj,
        "report_txt": report.report_txt,
        "source": report.source,
        "confidence": report.confidence,
        "model": report.model,
        "json_file_path": report.json_file_path,
        "txt_file_path": report.txt_file_path,
        "created_at": report.created_at,
    }
