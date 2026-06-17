"""
Pydantic校验模型 - 接口请求参数定义，响应格式约定为 { code: 200, data: ... }
"""
from pydantic import BaseModel, Field
from typing import Optional, List


# ==================== 认证（Auth） ====================
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=64)
    roleHint: Optional[str] = "village_grid"


# ==================== 告警（Alerts） ====================
class AlertPayload(BaseModel):
    title: Optional[str] = None
    location: Optional[str] = None
    ai_diagnosis: Optional[str] = None


class ResolveRequest(BaseModel):
    action_type: str = Field(..., pattern="^(VISITED|CALLED_FAMILY|FALSE_ALARM)$")
    handler_name: Optional[str] = "当前用户"
    remark: Optional[str] = ""


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
