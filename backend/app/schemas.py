"""
Pydantic校验模型 - 接口请求参数定义，响应格式约定为 { code: 200, data: ... }
"""
from pydantic import BaseModel, Field
from typing import Optional


# ==================== 认证（Auth） ====================
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=64)
    roleHint: Optional[str] = "village_grid"
    remember: bool = False                      # 勾选"记住登录"时签发长有效期 Token


class ChangePasswordRequest(BaseModel):
    """自助修改密码 - 所有登录用户可用"""
    old_password: str = Field(..., min_length=1, max_length=64)
    new_password: str = Field(..., min_length=6, max_length=64)


class ForgotPasswordRequest(BaseModel):
    """忘记密码 - 仅用户名，无邮箱（账号由管理员统一分配）"""
    username: str = Field(..., min_length=1, max_length=32)


# ==================== 告警（Alerts） ====================
class AlertPayload(BaseModel):
    title: Optional[str] = None
    location: Optional[str] = None
    ai_diagnosis: Optional[str] = None


class ResolveRequest(BaseModel):
    """告警处理请求 - P0 角色差异化

    网格员（village_grid）：action_type 取 VISITED/CALLED_FAMILY/FALSE_ALARM，填 remark（现场情况）
    村医（village_doctor）：action_type=MEDICAL_JUDGE，填 medical_judgment（医疗判断）+ need_transfer（是否送医）
    后端按角色校验 action_type 合法性，违反时返回 403。
    """
    action_type: str = Field(..., pattern="^(VISITED|CALLED_FAMILY|FALSE_ALARM|MEDICAL_JUDGE)$")
    handler_name: Optional[str] = "当前用户"
    remark: Optional[str] = ""
    # P0: 村医医疗判断专用字段（仅 action_type=MEDICAL_JUDGE 时使用）
    medical_judgment: Optional[str] = ""
    need_transfer: Optional[bool] = False


# ==================== 老人（Elders） ====================
class ElderListItem(BaseModel):
    elder_id: str
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    device_sn: Optional[str] = None
    gateway_sn: Optional[str] = None
    emergency_contact: Optional[str] = None
    risk_tags: list = []


# ==================== 走访任务（Visit Tasks） ====================
class FeedbackRequest(BaseModel):
    feedback: str = Field(..., min_length=1)


# ==================== 设备（Devices） ====================
class RebindRequest(BaseModel):
    device_sn: str
    elder_id: str = Field(..., min_length=1)


# ==================== 账号管理（Accounts） ====================
class CreateAccountRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=32)
    password: str = Field(..., min_length=6, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=50)
    role: str = Field(..., pattern="^(village_grid|village_doctor|admin|super_admin)$")
    village_id: Optional[int] = None


class UpdateAccountRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=50)
    role: Optional[str] = Field(None, pattern="^(village_grid|village_doctor|admin|super_admin)$")
    village_id: Optional[int] = None
    password: Optional[str] = Field(None, min_length=6, max_length=64)


class ToggleAccountRequest(BaseModel):
    status: str = Field(..., pattern="^(active|disabled)$")


# ==================== 专业 AI 分析报告 ====================
# 仅传输纯文本/数值结构化数据，不上传任何影像隐私内容

class VitalSigns(BaseModel):
    """生命体征（手环采集）"""
    heart_rate: Optional[int] = None        # 心率 bpm
    spo2: Optional[int] = None              # 血氧 %
    temperature: Optional[float] = None     # 体温 ℃
    blood_pressure: Optional[str] = None    # 血压 "收缩压/舒张压"


class FallData(BaseModel):
    """跌倒事件结构化数据 - 救援简报输入"""
    acceleration: Optional[float] = None            # 手环加速度峰值 (g)
    fall_location: Optional[str] = None             # 跌倒位置（卫生间/厨房/院子等）
    fall_time: Optional[str] = None                 # 跌倒发生时间
    vital_signs: Optional[VitalSigns] = None        # 跌倒后生命体征
    medical_history: Optional[str] = None           # 既往病史
    current_medications: Optional[str] = None       # 当前用药
    emergency_contact: Optional[str] = None         # 紧急联系人电话
    emergency_relation: Optional[str] = None        # 紧急联系人关系
    nearby_medical_resources: Optional[str] = None  # 周边医疗资源（村卫生室/乡镇卫生院距离）


class HealthData(BaseModel):
    """老人长期健康监测数据 - 长期健康分析输入"""
    bp_history: Optional[str] = None            # 血压历史（"140/90,138/88,..." 或文本描述）
    hr_history: Optional[str] = None            # 心率历史
    spo2_history: Optional[str] = None          # 血氧历史
    steps_avg: Optional[int] = None             # 日均步数
    sleep_hours: Optional[float] = None         # 日均睡眠时长
    medication_records: Optional[str] = None    # 服药记录（依从性描述）
    past_falls: Optional[str] = None            # 过往跌倒记录
    activity_summary: Optional[str] = None      # 活动量摘要
    data_period: Optional[str] = None           # 数据周期 "近30天"


class RescueBriefingRequest(BaseModel):
    """生成跌倒救援简报请求"""
    elder_id: str = Field(..., min_length=1)
    event_id: Optional[str] = None
    fall_data: FallData
    confidence: Optional[float] = None          # 跌倒置信度，低于阈值走本地兜底
    force_fallback: bool = False                # 强制使用本地模板（模拟断网）


class HealthAnalysisRequest(BaseModel):
    """生成长期健康分析报告请求"""
    elder_id: str = Field(..., min_length=1)
    days: int = Field(30, ge=1, le=180)         # 从 TDengine 拉取近 N 天数据
    health_data: Optional[HealthData] = None    # 可选，未传则后端从 TDengine + 档案组装
    force_fallback: bool = False


class FullAnalysisRequest(BaseModel):
    """连续两次独立调用请求（先救援简报再健康分析）"""
    elder_id: Optional[str] = None              # 可由路径参数提供
    fall_data: Optional[FallData] = None        # 跌倒数据，未传则用档案组装
    confidence: Optional[float] = None
    days: int = Field(30, ge=1, le=180)
    force_fallback: bool = False
