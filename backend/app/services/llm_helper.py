"""
大模型服务封装 —— 阿里云 DashScope (Qwen)
"""
import json
from datetime import datetime
from sqlalchemy import select
from app.models import Elder, HealthReport
from app.config import settings

QWEN_API_KEY = settings.qwen_api_key
QWEN_MODEL = settings.qwen_model_name

HEALTH_REPORT_PROMPT = """你是一位专业的乡村养老健康顾问。请根据以下老人的监测数据，生成一份月度健康评估报告。

老人信息：{elder_name}，{age}岁，{gender}
本月数据摘要：{data_summary}

请用通俗易懂的语言（村干部能看懂），不超过 200 字，包含：
1. 整体状态评价（一句话）
2. 需要关注的风险点（如有）
3. 建议措施（1-2 条）

不要使用"语速""泛音""基频"等专业术语。不要给出医疗诊断。"""


async def generate_health_report(elder_name: str, age: int, gender: str, data_summary: str) -> str:
    """调用 Qwen 大模型生成健康报告。失败时返回默认文本。"""
    if not QWEN_API_KEY or QWEN_API_KEY == "your-qwen-api-key":
        return f"经系统分析，{elder_name}本月整体状况良好。建议保持现有生活习惯，关注季节变化。（大模型 API 未配置，此为默认文本）"

    try:
        from dashscope import Generation

        prompt = HEALTH_REPORT_PROMPT.format(
            elder_name=elder_name,
            age=age,
            gender=gender,
            data_summary=data_summary,
        )

        response = Generation.call(
            model=QWEN_MODEL,
            prompt=prompt,
            max_tokens=300,
            temperature=0.7,
            api_key=QWEN_API_KEY,
        )

        # Redis API 计数
        try:
            from app.services.redis_client import increment_api_counter
            await increment_api_counter("qwen", "api_calls")
            if response.status_code == 200 and hasattr(response.output, 'usage'):
                total = getattr(response.output.usage, 'total_tokens', 0) or 0
                if total:
                    await increment_api_counter("qwen", "tokens", total)
        except Exception:
            pass

        if response.status_code == 200:
            return response.output.text.strip()
        else:
            print(f"[LLM] 调用失败: {response.message}")
            return f"经系统分析，{elder_name}本月整体状况良好。（AI 报告生成失败，此为默认文本）"

    except ImportError:
        return f"经系统分析，{elder_name}本月整体状况良好。（dashscope SDK 未安装）"
    except Exception as e:
        print(f"[LLM] 异常: {e}")
        return f"经系统分析，{elder_name}本月整体状况良好。（AI 报告生成异常）"


async def generate_all_reports(db_session_factory):
    """为所有老人生成本月 AI 报告。由 APScheduler 定时触发。"""
    async with db_session_factory() as db:
        elders = (await db.execute(select(Elder))).scalars().all()
        month = datetime.now().strftime("%Y-%m")

        for e in elders:
            # 检查本月是否已生成
            existing = (await db.execute(
                select(HealthReport).where(
                    HealthReport.elder_id == e.elder_id,
                    HealthReport.report_month == month,
                )
            )).scalar_one_or_none()
            if existing:
                continue

            # 构造数据摘要（Phase 2 从已有字段提取）
            data_summary = f"年龄{e.age}岁，住址{e.address}。"
            if e.medical_history:
                data_summary += f"既往病史：{e.medical_history}。"

            # 调用大模型
            ai_text = await generate_health_report(
                e.name, e.age or 0, e.gender or "未知", data_summary
            )

            # 存储
            tags = json.loads(e.risk_tags) if e.risk_tags else []
            db.add(HealthReport(
                elder_id=e.elder_id,
                report_month=month,
                risk_tags=json.dumps(tags, ensure_ascii=False),
                ai_summary=ai_text,
                data_source="手环活动记录 + 门磁数据",
                generated_by=QWEN_MODEL,
                created_at=datetime.now().isoformat(),
            ))

        await db.commit()
        print(f"[LLM] 已为 {len(elders)} 位老人生成 AI 报告")
